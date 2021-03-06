from __future__ import print_function
import os
import time
import socket
import paramiko
import platform
import threading
from scp import SCPClient

rpi_hostname = 'raspberrypi.local'
rpi_user = "pi"
rpi_password = ""
rpi_ip = socket.gethostbyname(rpi_hostname)


def running_on_rpi():
    return platform.uname()[4][:3] == 'arm'


def create_ssh_client(server, user, password, port=22):
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
    ssh = create_ssh_client(rpi_ip, rpi_user, rpi_password)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command, get_pty=True)
    if silent:
        return ssh_stdin, ssh_stdout, ssh_stderr
    if keep_alive_duration:
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
    if keep_alive_duration:
        t.join()


def upload_dir_simple(local_path, remote_path, recursive=True):
    ssh = create_ssh_client(rpi_ip, rpi_user, rpi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(files=local_path, remote_path=remote_path, recursive=recursive)


def upload_dir(local_path, remote_path, recursive=True, hidden_files=False):
    ssh = create_ssh_client(rpi_ip, rpi_user, rpi_password)
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
    ssh = create_ssh_client(rpi_ip, rpi_user, rpi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(remote_path=remote_path, local_path=local_path, recursive=True)
    if clear_afterwards:
        clear_dir(remote_path)


def clear_dir(remote_path):
    if remote_path[-1] != '/':
        remote_path += '/'
    ssh = create_ssh_client(rpi_ip, rpi_user, rpi_password)
    with ssh.open_sftp() as sftp:
        files_to_remove = sftp.listdir(path=remote_path)
        for delete_file in files_to_remove:
            sftp.remove(remote_path + delete_file)


def sync_project():
    local_dir = os.path.dirname(os.path.abspath(__file__))
    remote_dir = '/home/pi/pi_tools'
    print("Syncing {} to {}".format(local_dir, remote_dir))
    upload_dir(local_dir, remote_dir, recursive=False)


if __name__ == "__main__":
    sync_project()
