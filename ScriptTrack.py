from __future__ import print_function
import os

if not os.uname()[4][:3] == 'arm':

    print("1) Uploading code ...")
    import DeployTools
    try:
        DeployTools.sync_project()
    except:
        pass

    print("2) Acquiring data ...")
    ssh_command = "python3 ~/BallDetector/ScriptTrack.py"
    DeployTools.ssh(ssh_command, keep_alive_duration=20)

    print("3) Download data ...")
    DeployTools.download_dir("/home/pi/BallsTracked", "/home/anders/RaspberryPi", clear_afterwards=True)

else:
    import Tracker
    Tracker.start_rpi_tracker()