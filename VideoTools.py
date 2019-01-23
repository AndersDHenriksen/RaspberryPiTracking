from __future__ import print_function
import CameraTools
from picamera import PiCamera
from time import sleep, strftime, time
import numpy as np
import os

def time_stamp():
    return strftime("%Y%m%d_%H%M%S")


def initiate_camera():
    resolution = (640, 480)
    framerate = 90
    shutter_speed = 4000
    sensor_mode = 7

    camera = PiCamera(resolution=resolution, framerate=framerate, sensor_mode=sensor_mode)
    # camera.shutter_speed = shutter_speed

    camera.start_preview()
    sleep(2)  # Give time to auto gain
    camera.stop_preview()

    print(CameraTools.get_camera_settings(camera))

    return camera
    # ToDo consider not stopping camera and storing it, maybe as function attribute or through decorator


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
            camera.start_recording('/home/pi/Videos/video_' + time_stamp() + '.avi', format='h264')
        else:
            camera.start_recording('/home/pi/Videos/video_' + time_stamp() + '.raw', format='bgr')
        camera.wait_recording(duration)
        camera.stop_recording()


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
