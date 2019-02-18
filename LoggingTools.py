import os
import cv2
import tarfile
from time import strftime
from datetime import datetime, timedelta
import CameraTools
import SystemTools
import json
import threading
import logging
from fractions import Fraction


class PeriodicSaver:

    def __init__(self, video):
        self.periodic_save_dir = '/home/pi/Logs/PeriodicInfo/'
        os.makedirs(self.periodic_save_dir, exist_ok=True)
        self.video = video
        self.camera = video.camera
        self.last_idx = 0
        self.counter = 0
        self.next_save_time = self._get_next_save_time()

    def _get_next_save_time(self):
        existing_logs = sorted(os.listdir(self.periodic_save_dir))
        if len(existing_logs) == 0:
            return datetime.now()
        last_save_time = datetime.strptime(existing_logs[-1], "%Y%m%d_%H%M%S.tar")
        return last_save_time + timedelta(hours=.5)

    def __call__(self, idx, image):
        self.counter += 1
        new_idx = idx % 1000
        skip = new_idx > self.last_idx
        self.last_idx = new_idx
        if skip or datetime.now() < self.next_save_time:
            return

        save_thread = threading.Thread(target=self._save_log, args=(image, ))
        save_thread.start()  # TODO is it ok not to join the thread

        # Update next_save_time
        self.next_save_time = datetime.now() + timedelta(hours=.5)

    def _save_log(self, image):
        print("Saving periodic log tar ...")
        # Save image
        save_path_name = self.periodic_save_dir + strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(save_path_name + ".png", image)

        # Save json
        camera_settings = CameraTools.get_camera_settings(self.camera, silent=True)
        system_info = SystemTools.get_system_info(self.video, self)
        json_dict = {'Camera Settings': camera_settings, 'System Info': system_info}
        with open(save_path_name + '.json', 'w') as fp:
            json.dump(json_dict, fp, sort_keys=True, indent=4, cls=ExtendedJsonEncoder)

        # Tar
        with tarfile.open(save_path_name + '.tar', mode='w') as tar:
            for ext in [".png", ".json"]:
                tar.add(save_path_name + ext, arcname=(save_path_name + ext).split("/")[-1])
                os.remove(save_path_name + ext)

        # Remove of too old log tars
        existing_logs = sorted(os.listdir(self.periodic_save_dir))
        for file in existing_logs[:-50]:
            os.remove(self.periodic_save_dir + file)


class ExtendedJsonEncoder(json.JSONEncoder):
    def default(self, entry):
        if isinstance(entry, Fraction):
            return str(entry)
        else:
            super().default(self, entry)


def setup_logger():
    log_dir = "/home/pi/Logs/"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=log_dir + 'tracker.log',
                        format='%(asctime)s | %(module)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
