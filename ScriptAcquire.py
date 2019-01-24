from __future__ import print_function
import os

acquire = "video"

assert acquire in ["image", "video", "numpy"]

if not os.uname()[4][:3] == 'arm':
    print("1) Uploading code ...")
    import DeployTools
    DeployTools.sync_project()

    print("2) Acquiring data ...")
    ssh_command = "python3 ~/BallDetector/ScriptAcquire.py"
    DeployTools.ssh(ssh_command)

    print("3) Download data ...")
    rpi_data_folder = {'image': "/home/pi/Pictures", "video": "/home/pi/Videos", "numpy": "/home/pi/NumpyData"}
    DeployTools.download_dir(rpi_data_folder[acquire], DeployTools.home() + "/RaspberryPi", clear_afterwards=True)

    if acquire == "numpy":
        print("4) Processing data ...")
        import DataTools
        DataTools.create_video()

    print("5) Done")

else:
    import VideoTools
    if acquire == 'image':
        VideoTools.acquire_image()
    elif acquire == 'video':
        VideoTools.acquire_video_clip(compress=True)
    elif acquire == 'numpy':
        VideoTools.acquire_numpy_array()
