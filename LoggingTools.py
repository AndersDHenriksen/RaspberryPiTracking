import os
import cv2
import tarfile
from time import strftime
from datetime import datetime, timedelta
import CameraTools
import SystemTools
import json


class PeriodicSaver:

    def __init__(self, video):
        self.periodic_save_dir = '/home/pi/Logs/'
        self.camera = video.camera
        self.last_idx = 0
        self.next_save_time = self._get_next_save_time()

    def _get_next_save_time(self):
        existing_logs = os.listdir(self.periodic_save_dir)
        last_file = existing_logs[-1] if len(existing_logs) else '20190101_000000.tar'
        last_save_time = datetime.strptime(last_file, "%Y%m%d_%H%M%S.tar")
        return last_save_time + timedelta(hours=.5)

    def __call__(self, idx, image):
        new_idx = idx % 1000
        skip = new_idx > self.last_idx
        self.last_idx = new_idx
        if skip or datetime.now() < self.next_save_time:
            return

        # TODO spawn thread to handle save_log  # TODO is it ok not to join the thread

    def _save_log(self, image):
        print("Saving periodic log tar ...")
        # Save image
        save_path_name = self.periodic_save_dir + strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(save_path_name + ".png", image)

        # Save json
        camera_settings = CameraTools.get_camera_settings(self.camera, silent=True)
        system_info = SystemTools.get_system_info()
        json_dict = {'Camera Settings': camera_settings, 'System Info': system_info}
        with open(save_path_name + '.json', 'w') as fp:
            json.dump(json_dict, fp, sort_keys=True, indent=4)

        # Tar
        with tarfile.open('packages.tar', mode='w') as tar:
            for ext in [".png", ".json"]:
                tar.add(save_path_name + ext)
                os.remove(save_path_name + ext)

        # Remove of too old log tars
        existing_logs = os.listdir(self.periodic_save_dir)
        for file in existing_logs[:-50]:
            os.remove(self.periodic_save_dir + file)

        # Update next_save_time
        self.next_save_time + timedelta(hours=.5)


def get_acquire_fps(video, wait_time=5):
    video
