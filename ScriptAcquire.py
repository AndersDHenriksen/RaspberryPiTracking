from __future__ import print_function
import os


if not os.uname()[4][:3] == 'arm':
    print("1) Uploading code ...")
    import DeployTools
    DeployTools.sync_project()

    print("2) Acquiring data ...")
    ssh_command = "python3 ~/BallDetector/ScriptAcquire.py"
    DeployTools.ssh(ssh_command)

    print("3) Download data ...")
    DeployTools.download_dir("/home/pi/NumpyData", "/home/anders/RaspberryPi", clear_afterwards=True)
    # DeployTools.download_dir("/home/pi/Pictures", "/home/anders/RaspberryPi", clear_afterwards=True)
    # DeployTools.download_dir("/home/pi/Videos", "/home/anders/RaspberryPi", clear_afterwards=True)
    # DeployTools.download_dir("/home/pi/BallsTracked", "/home/anders/RaspberryPi", clear_afterwards=True)

    print("4) Processing data ...")
    import DataTools
    DataTools.create_video()

    print("5) Done")

else:
    import VideoTools
    VideoTools.acquire_numpy_array()
    # VideoTools.acquire_video_clip(compress=False)
    # VideoTools.acquire_image()