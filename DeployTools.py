from __future__ import print_function
import paramiko
import time
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


def kill_all_python():
    ssh_kill_command = "ps -ef | grep 'python' | awk '{print $2}' | xargs sudo kill"
    ssh(ssh_kill_command, silent=True)


def ssh(command, silent=False, keep_alive_duration=None):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    if silent:
        return ssh_stdin, ssh_stdout, ssh_stderr
    start_time = time.time()
    print("stdout:")
    for line in ssh_stdout:
        print(line.rstrip())
        if keep_alive_duration is not None and time.time() - start_time > keep_alive_duration:
            ssh.close()
    for name, stream in zip(["stdin", "stderr"], [ssh_stdin, ssh_stderr]):
        if stream.readable():
            print(name + ":")
            print(stream.read())


def upload_dir(local_path, remote_path):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(files=local_path, remote_path=remote_path, recursive=True)


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
    upload_dir(local_dir, remote_dir)


if __name__ == "__main__":
    sync_project()
