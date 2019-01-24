from __future__ import print_function
import os

if not os.uname()[4][:3] == 'arm':

    print("1) Uploading code ...")
    import DeployTools
    DeployTools.sync_project()

    print("2) Acquiring data ...")
    ssh_command = "python3 ~/BallDetector/ScriptTrack.py"
    DeployTools.ssh(ssh_command, keep_alive_duration=60)

    print("3) Download data ...")
    DeployTools.download_dir("/home/pi/BallsTracked", DeployTools.home() + "/RaspberryPi", clear_afterwards=True)

else:
    import Tracker
    Tracker.start_rpi_tracker()