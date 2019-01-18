import os
from glob import glob
import numpy as np
import cv2

data_dir = "/home/anders/RaspberryPi/NumpyData/"


def create_video(local_dir=None):
    if local_dir is None:
        local_dir = data_dir + sorted(os.listdir(data_dir))[-1]
    if local_dir[-1] != '/':
        local_dir += '/'

    # Load numpy file(s)
    if os.path.exists(local_dir + "data.npy"):
        frames = np.load(local_dir + "data.npy")
    else:
        data_files = sorted(glob(local_dir + "*.npy"))
        frames = np.concatenate([np.load(data_file) for data_file in data_files])

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(local_dir + 'video.avi', fourcc, 90.0, (640, 480))
    # Write frames and close video
    for frame in frames:
        out.write(frame)
    out.release()


if __name__ == '__main__':
    create_video()
