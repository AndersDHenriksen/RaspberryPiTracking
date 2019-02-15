# import the necessary packages
from __future__ import print_function
try:
    from picamera.array import PiRGBAnalysis
    from picamera import PiCamera
except ImportError:
    PiRGBAnalysis = object
    print("picamera not imported in pivideobufferstream")
from time import sleep, strftime
from threading import Lock
from datetime import datetime
import numpy as np
import DataTools
import VideoTools


class PiVideoBufferStream:
    def __init__(self, resolution=None, framerate=None, shutter_speed=None, buffer_size=300):
        self.camera = VideoTools.initiate_camera(resolution, framerate, shutter_speed)
        self.ring_buffer = RingBuffer(self.camera, buffer_size)

    def start(self):
        self.ring_buffer.start_stream()

    def record_full_buffer(self):
        self.start()
        while not self.ring_buffer.filled_up():
            sleep(0.005)
        self.stop()
        return self.ring_buffer.index_ring_buffer, self.ring_buffer.frame_ring_buffer

    def read_new(self):
        return self.ring_buffer.read_new()

    def read_idx(self, idx):
        return self.ring_buffer.read_idx(idx)

    def read_timestamp(self, idx):
        return self.ring_buffer.get_timestamp(idx)

    def reset_buffer(self):
        self.ring_buffer.discard_all_frames()

    def delete_buffer(self):
        self.ring_buffer.discard_all_frames()
        del self.ring_buffer

    def save_track(self, first_idx, last_idx):
        print("Saving video")
        idxs = np.arange(first_idx, last_idx + 1)
        self.ring_buffer.save_video(idxs)

    def stop(self):
        self.camera.stop_recording()
        self.camera.close()


class RingBuffer(PiRGBAnalysis):
    def __init__(self, camera, buffer_size):
        super(RingBuffer, self).__init__(camera)
        self.camera = camera
        self.buffer_size = buffer_size
        self.thread_lock = Lock()
        self._dprior = 4
        self._init_ring_buffer()

    def analyze(self, array):
        self._enqueue_frame(array)

    @VideoTools.temp_disable_video
    def _init_ring_buffer(self):
        with self.thread_lock:
            if not hasattr(self, 'frame_ring_buffer'):
                resolution = self.camera.resolution
                self.frame_ring_buffer = np.zeros((self.buffer_size, resolution[1], resolution[0], 3), dtype=np.uint8)
            self.insert_idx = 0
            self.index_ring_buffer = np.zeros(self.buffer_size, dtype=np.int)
            self.timestamp_ring_buffer = self.buffer_size * [None]
            self.newest_frame_buffer_index = 0
            self.newest_frame_yielded = True

    def _enqueue_frame(self, array):
        with self.thread_lock:
            self.insert_idx = (self.insert_idx + 1) % self.buffer_size
            self.newest_frame_buffer_index += 1
            self.index_ring_buffer[self.insert_idx] = self.newest_frame_buffer_index
            self.frame_ring_buffer[self.insert_idx] = array
            self.timestamp_ring_buffer[self.insert_idx] = datetime.now().isoformat()  # Alternative utcnow().isoformat()
            self.newest_frame_yielded = False

    def read_new(self):
        while self.newest_frame_yielded:
            sleep(0.01)
        with self.thread_lock:
            self.newest_frame_yielded = True
            yeild_idx = self.insert_idx
            prior_idx = (yeild_idx - self._dprior) % self.buffer_size
            return self.index_ring_buffer[yeild_idx], self.frame_ring_buffer[yeild_idx], self.frame_ring_buffer[prior_idx]

    def read_idx(self, idx):
        with self.thread_lock:
            yeild_idx = np.flatnonzero(idx == self.index_ring_buffer)
            if not yeild_idx.size:
                return None, None, None
            yeild_idx = yeild_idx[0]
            prior_idx = (yeild_idx - self._dprior) % self.buffer_size
            if self.index_ring_buffer[yeild_idx] != self.index_ring_buffer[prior_idx] + self._dprior:
                return None, None, None
            return self.index_ring_buffer[yeild_idx], self.frame_ring_buffer[yeild_idx], self.frame_ring_buffer[prior_idx]

    def get_timestamp(self, idx):
        with self.thread_lock:
            yeild_idx = np.flatnonzero(idx == self.index_ring_buffer)
            if not yeild_idx.size:
                return None
            return self.timestamp_ring_buffer[yeild_idx[0]]

    def current_frame_idx(self):
        with self.thread_lock:
            return self.newest_frame_buffer_index

    @VideoTools.temp_disable_video
    def save_video(self, idxs):
        frame_iterator = (self.read_idx(idx)[1] for idx in idxs)
        save_path = DataTools.rpi_video_dir + strftime("%Y%m%d_%H%M%S") + ".avi"  # For some reason mp4 crashes here
        DataTools.write_video(save_path, frame_iterator, codec='H264')

    def start_stream(self):
        self.camera.start_recording(self, format="bgr")

    def discard_all_frames(self):
        self._init_ring_buffer()

    def filled_up(self):
        return self.newest_frame_buffer_index >= self.buffer_size


class MockBufferStream:
    def __init__(self, data_path):
        self._dprior = 4
        if data_path.endswith('.npy'):
            self.frames = np.load(data_path)
        elif data_path.endswith('.raw'):
            self.frames = np.fromfile(data_path, dtype=np.uint8).reshape((-1, 480, 640, 3))
        elif data_path.endswith('.avi') or data_path.endswith('.mp4'):
            import cv2
            frames, frame_available = [], True
            cap = cv2.VideoCapture(data_path)
            while cap.isOpened() and frame_available:
                frame_available, frame = cap.read()
                frames.append(frame)
            cap.release()
            self.frames = np.array(frames[:-1])
        else:
            raise NotImplementedError
        assert self.frames.size
        self.index = np.arange(self.frames.shape[0])
        self.yield_idx = self._dprior

    def start(self):
        pass

    def stop(self):
        pass

    def delete_buffer(self):
        pass

    def read_new(self):
        self.yield_idx += 1
        if self.yield_idx % 2 == 0:
            self.yield_idx += 1
        return self.read_idx(self.yield_idx)

    def read_idx(self, idx):
        if idx < self._dprior or idx >= self.frames.shape[0]:
            raise StopIteration
        return idx, self.frames[idx], self.frames[idx - self._dprior]

    def read_timestamp(self, idx):
        return datetime.now().isoformat()

    def reset_buffer(self):
        self.yield_idx += 90

    def save_track(self, *args, **kwargs):
        pass

