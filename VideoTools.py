from __future__ import print_function
import CameraTools
try:
    from picamera import PiCamera
except ImportError:
    print("picamera not imported in VideoTools")
from time import sleep, strftime, time
import numpy as np
import os
import functools


def time_stamp():
    return strftime("%Y%m%d_%H%M%S")


def initiate_camera(resolution=None, fps=None, sensor_mode=None, zoom=None, shutter_speed=None):
    resolution = resolution or (800, 450)
    framerate = fps or 90
    sensor_mode = sensor_mode or 6
    zoom6 = 0.5 - resolution[0] / 2560, 0.5 - resolution[1] / 1440, resolution[0] / 1280, resolution[1] / 720
    zoom = zoom or (zoom6 if sensor_mode == 6 else (0, 0, 1, 1))

    assert resolution[0] * 9 == resolution[1] * 16, "Resolution must 16:9"
    camera = PiCamera(resolution=resolution, framerate=framerate, sensor_mode=sensor_mode)
    camera.zoom = zoom
    if shutter_speed is not None:
        camera.shutter_speed = shutter_speed

    camera.start_preview()
    sleep(2)  # Give time to auto gain
    camera.stop_preview()

    # current_output = np.empty((resolution[0], resolution[1], 3), dtype=np.uint8)
    # camera.capture(current_output, format='bgr')
    # mean_intensity = current_output.mean()
    # if mean_intensity < 40:
    #     print("Increasing gains to max")
    #     camera.iso = 800
    #     camera.exposure_compensation = 25
    #     sleep(2)

    CameraTools.get_camera_settings(camera)
    return camera
    # ToDo consider not stopping camera and storing it, maybe as function attribute or through decorator


def temp_disable_video(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Disable camera
        is_recording = self.camera.recording
        if is_recording:
            self.camera.stop_recording()

        value = func(self, *args, **kwargs)

        # Enable camera
        if is_recording:
            self.start_stream()

        return value
    return wrapper


def see_preview(duration=5):
    camera = initiate_camera()
    camera.start_preview()
    sleep(duration)
    camera.stop_preview()


def acquire_image():
    with initiate_camera() as camera:
        camera.capture('/home/pi/Pictures/image_' + time_stamp() + '.png')


def acquire_video_clip(duration=8, compress=True):
    with initiate_camera() as camera:
        print("Acquiring video ... ")
        if compress:
            h264_stream = '/home/pi/Videos/video_' + time_stamp() + '.h264'
            camera.start_recording(h264_stream, format='h264')
        else:
            camera.start_recording('/home/pi/Videos/video_' + time_stamp() + '.raw', format='bgr')
        camera.wait_recording(duration)
        camera.stop_recording()
        if not compress:
            return
        # Wrap h264 stream to mp4 container
        print("Containerizing video ...")
        import subprocess
        mp4_container = h264_stream[:-4] + 'mp4'
        ffmpeg_command = 'ffmpeg -r 90 -i "{}" -c:v copy -f mp4 "{}"'.format(h264_stream, mp4_container)
        subprocess.call(ffmpeg_command, shell=True)
        os.remove(h264_stream)


def acquire_numpy_array_old(duration=8):
    from imutils.video.pivideostream import PiVideoStream
    fps = 90
    vs = PiVideoStream(resolution=(640, 480), framerate=fps).start()
    vs.camera.shutter_speed = 4000
    sleep(2)
    vs.start()
    save_dir = '/home/pi/NumpyData/' + time_stamp()
    os.makedirs(save_dir)
    print("Acquiring + saving uncompressed video ... ")
    example_frame = vs.read()
    assert example_frame.size
    frames_shape = [fps * duration] + list(example_frame.shape)
    frames = np.empty(frames_shape, dtype=np.uint8)
    for i in range(fps * duration):
        last_frame_time = time()
        frames[i] = vs.read()
        sleep(1.0/fps - (time() - last_frame_time))
    vs.stop()
    np.save(save_dir + '/data.npy', frames)


def acquire_numpy_array(duration=8):
    from pivideobufferstream import PiVideoBufferStream
    fps = 90
    print("Acquiring uncompressed video ... ")
    vs = PiVideoBufferStream(resolution=(640, 480), framerate=fps, buffer_size=fps * duration)
    CameraTools.get_camera_settings(vs.camera)
    indexes, frames = vs.record_full_buffer()
    print("Saving uncompressed video ... ")
    save_dir = '/home/pi/NumpyData/' + time_stamp()
    os.makedirs(save_dir)
    np.save(save_dir + '/data.npy', frames)


# Other ideas:
# https://picamera.readthedocs.io/en/release-1.13/recipes2.html#splitting-to-from-a-circular-stream
# https://picamera.readthedocs.io/en/release-1.13/api_streams.html
