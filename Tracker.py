import numpy as np
import cv2
import VisionToolsMini as vt
from time import sleep, time
from uuid import getnode

h = 0
pixels_per_meter = 463  # at camera height 2.87 m
save_captured_tracks = True

fps = 90
g = 9.82
expected_ball_width = int(0.043 * pixels_per_meter)
expected_area = int(np.pi / 4 * expected_ball_width ** 2)


def distance(v):
    if h == 0:
        d = v ** 2 / g
        return d

    theta = np.array(0, 45) * np.pi / 180
    vx = v * np.cos(theta)
    vy = v * np.sin(theta)
    ds = vx * (vy + np.sqrt(vy ** 2 - 2 * h * g)) / g
    return ds.max()


def ball_finder(current_image, prior_image):
    if current_image is None or prior_image is None:
        return None

    # Detect difference
    difference_bgr = cv2.subtract(current_image, prior_image)
    difference = cv2.cvtColor(difference_bgr, cv2.COLOR_BGR2GRAY)

    # Simple dummy check that triggers just om image motion
    if 0:
        mean_diff = difference.mean()
        if mean_diff > 7:
            return (int(mean_diff), int(mean_diff/2))
        else:
            return None

    # Find ball u coordinates
    ball_u_start, ball_u_end, threshold_u = find_ball_1d_limits(difference, axis=0)
    if ball_u_start is None:
        return None

    # Find ball v-cor cluster
    difference_reduced = difference[:, ball_u_start:ball_u_end + 1]
    ball_v_start, ball_v_end, threshold_v = find_ball_1d_limits(difference_reduced, axis=1)
    if ball_v_start is None:
        return None

    # 1. sanity check area
    difference_ball = difference_reduced[ball_v_start:ball_v_end, :]
    threshold_min = min(threshold_u, threshold_v)
    bw_ball = difference_ball > threshold_min
    # Originally used vt.bw_area_filter(bw_ball, output='area') but this caused memory error
    if min(bw_ball.shape) < 11 or bw_ball.sum() < 4 * expected_area / 5:
        return None

    # 2. sanity thick middle
    if np.mean(bw_ball[5:-5, :].sum(axis=1) > 3 * expected_ball_width / 4) < 0.75 or \
       np.mean(bw_ball[:, 5:-5].sum(axis=0) > 3 * expected_ball_width / 4) < 0.75:
        return None

    side_lengths = np.array([ball_u_end - ball_u_start, ball_v_end - ball_v_start])
    if side_lengths.max() < 1.5 * expected_ball_width:
        return (ball_u_start + ball_u_end) / 2, (ball_v_start + ball_v_end) / 2

    # 3. sanity check pixel distribution
    inner_length = np.linalg.norm((side_lengths - expected_ball_width).clip(min=0))
    expected_size = int(expected_ball_width * inner_length + expected_area)
    threshold = np.sort(difference_ball.ravel())[-expected_size]
    bw_ball = difference_ball > threshold
    track_widths = bw_ball.sum(axis=side_lengths.argmax())[expected_ball_width//2:-expected_ball_width//2]
    if np.std(track_widths) > 2.5:
        return None
    return (ball_u_start + ball_u_end)/2, (ball_v_start + ball_v_end)/2
    # TODO if shutter speed is known velocity can be determined from ball size. Maybe if ball u > widht/3 call in ball detection directly


def find_ball_1d_limits(difference, axis):
    assert axis in [0, 1]
    partition_element = difference.shape[axis] - (expected_ball_width - 4)
    difference_partitioned = np.partition(difference, kth=partition_element, axis=axis)
    if axis == 0:
        ball_intensity_u = difference_partitioned[-(expected_ball_width - 4):, :].mean(axis=axis)
    else:
        ball_intensity_u = difference_partitioned[:, -(expected_ball_width - 4):].mean(axis=axis)
    # Open morph, properly not needed
    ball_u = vt.morph('open', ball_intensity_u, (1, expected_ball_width))
    # Find ball cluster
    sorted_ball_u = np.sort(ball_u)
    window_size = vt.intr(expected_ball_width / 3)
    jump = np.max(sorted_ball_u[window_size:] - sorted_ball_u[:-window_size])
    if jump < 10:
        return None, None, None
    threshold = min(40, int(sorted_ball_u[sorted_ball_u.size // 4] + 2 * jump / 3))
    ball_u_clusters = vt.find_clusters(ball_u > threshold, allowed_jump=2, min_size=expected_ball_width)
    if not len(ball_u_clusters):
        return None, None, None
    ball_u_cluster = max(ball_u_clusters, key=len)
    ball_u_start, ball_u_end = ball_u_cluster[0], ball_u_cluster[-1]
    return ball_u_start, ball_u_end, threshold


def analyze_video(video):
    video.start()
    mac_address = getnode()
    print("Tracker started ... ")
    while True:
        ball_track_iuv = []
        idx, current_frame, prior_frame = video.read_new()
        ball_location_uv = ball_finder(current_frame, prior_frame)
        if ball_location_uv is None:
            continue
        ball_track_iuv.append([idx, ball_location_uv[0], ball_location_uv[1]])

        # Backtrack
        backtrack_idx = idx
        while True:
            backtrack_idx -= 1
            _, current_frame, prior_frame = video.read_idx(backtrack_idx)
            ball_location_uv = ball_finder(current_frame, prior_frame)
            if ball_location_uv is None:
                break
            ball_track_iuv.insert(0, [backtrack_idx, ball_location_uv[0], ball_location_uv[1]])

        # Forward track
        forward_idx = idx
        while True:
            forward_idx += 1
            attemps = 0
            current_frame = None
            while attemps < 5 and current_frame is None:
                _, current_frame, prior_frame = video.read_idx(forward_idx)
                attemps += 1
                if current_frame is None:
                    sleep(0.5/fps)
            ball_location_uv = ball_finder(current_frame, prior_frame)
            if ball_location_uv is None:
                break
            ball_track_iuv.append([forward_idx, ball_location_uv[0], ball_location_uv[1]])

        # Calculate velocity
        if len(ball_track_iuv) < 3:
            continue
        ball_track_iuv = np.array(ball_track_iuv)
        du = np.diff(ball_track_iuv[:, 1])
        if du.mean() < 5 or du.min() < 2:
            continue
        delta_iuv = ball_track_iuv[-1, :] - ball_track_iuv[0, :]
        theta_rad = np.arctan2(-delta_iuv[2], delta_iuv[1])  # Positive theta means ball flying toward top pixel row
        velocity_ms = np.linalg.norm(delta_iuv[1:]) / delta_iuv[0] * fps / pixels_per_meter
        distance_max_m = distance(velocity_ms)
        if theta_rad > np.pi / 3 or theta_rad < - np.pi / 3:
            print("Club backswing detected")
            video.reset_buffer()
            continue

        print("=====================================================")
        print("Ball detected for MAC-address: {}".format(mac_address))
        print("Ball frame index: {:.0f}".format(ball_track_iuv[:, 0].mean()))
        print("Ball launch angle: {:.1f}".format(theta_rad * 180 / np.pi))
        print("Ball velocity: {:.1f} m/s".format(velocity_ms))
        print("Ball carry: {:.1f} m".format(distance_max_m))
        print("=====================================================")
        if save_captured_tracks:
            video.save_track(ball_track_iuv[0, 0] - 10, ball_track_iuv[-1, 0] + 10)
        video.reset_buffer()


def start_rpi_tracker(debug=False):
    from pivideobufferstream import PiVideoBufferStream
    if debug:
        import Tracker
        PiVideoBufferStream.read_new = debug_read_decorator(PiVideoBufferStream.read_new)
        PiVideoBufferStream.read_idx = debug_read_decorator(PiVideoBufferStream.read_idx)
        Tracker.ball_finder = debug_ball_finder_decorator(Tracker.ball_finder)

    video_stream = PiVideoBufferStream()
    try:
        analyze_video(video_stream)
    finally:
        print("Tracker stopped.")
        video_stream.stop()


def debug_read_decorator(func):
    def read(*args, **kwargs):
        result = func(*args, **kwargs)
        print("Reading frame {}".format(result[0]))
        return result
    return read


def debug_ball_finder_decorator(func):
    def ball_finder(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        print("Analyzed frame in {:.0f} ms. Ball found: {}.".format(1000 * (end_time - start_time), result is not None))
        return result
    return ball_finder


if __name__ == "__main__":
    from pivideobufferstream import MockBufferStream
    data_path = '/home/ahe/GoogleDrive/TrackMan/04. RangeShortShots/video_20190123_094456.avi'
    video = MockBufferStream(data_path)
    try:
        analyze_video(video)
    except StopIteration:
        print("Video analysis complete of: {}".format(data_path))
