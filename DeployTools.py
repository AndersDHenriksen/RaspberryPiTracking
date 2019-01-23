from __future__ import print_function
import time
import os
import threading
import paramiko
from scp import SCPClient

rpi_ip = "192.168.16.118"
rpi_user = "pi"
rpi_password = "raspberry"


def createSSHClient(server, user, password, port=22):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client


def close_ssh_when_time(ssh, time_remaining):
    time.sleep(time_remaining)
    ssh.close()


def kill_all_python():
    ssh_kill_command = "ps -ef | grep 'python' | awk '{print $2}' | xargs sudo kill"
    ssh(ssh_kill_command, silent=True)


def home():
    return os.path.expanduser("~")


def ssh(command, silent=False, keep_alive_duration=None):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command, get_pty=True)
    if silent:
        return ssh_stdin, ssh_stdout, ssh_stderr
    t = threading.Thread(target=close_ssh_when_time, args=(ssh, keep_alive_duration), daemon=True)
    t.start()
    print("stdout:")
    for line in ssh_stdout:
        print(line.rstrip())
    for name, stream in zip(["stdin", "stderr"], [ssh_stdin, ssh_stderr]):
        if stream.readable():
            stream_message = stream.read()
            if stream_message:
                print(name + ":\n" + stream_message)
    t.join()


def upload_dir_simple(local_path, remote_path, recursive=True):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(files=local_path, remote_path=remote_path, recursive=recursive)


def upload_dir(local_path, remote_path, recursive=True, hidden_files=False):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    folders = []
    with SCPClient(ssh.get_transport()) as scp:
        for element in os.listdir(local_path):
            if not hidden_files and element[0] == '.':
                continue
            if os.path.isdir(element):
                if recursive:
                    folders.append(element)
                continue
            scp.put(files=os.path.join(local_path, element), remote_path=remote_path, recursive=False)
    [upload_dir(os.path.join(local_path, f), os.path.join(remote_path, f), recursive, hidden_files) for f in folders]


def download_dir(remote_path, local_path, clear_afterwards=False):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(remote_path=remote_path, local_path=local_path, recursive=True)
    if clear_afterwards:
        clear_dir(remote_path)


def clear_dir(remote_path):
    if remote_path[-1] != '/':
        remote_path += '/'
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    with ssh.open_sftp() as sftp:
        files_to_remove = sftp.listdir(path=remote_path)
        for delete_file in files_to_remove:
            sftp.remove(remote_path + delete_file)


def sync_project():
    local_dir = '/home/ahe/Projects/RaspberryPiTracking/'
    remote_dir = '/home/pi/BallDetector'
    print("Syncing {} to {}".format(local_dir, remote_dir))
    upload_dir(local_dir, remote_dir, recursive=False)


if __name__ == "__main__":
    sync_project()
