from __future__ import print_function
import paramiko
from scp import SCPClient

rpi_ip = "192.168.2.227"
rpi_user = "pi"
rpi_password = "raspberry"


def createSSHClient(server, user, password, port=22):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client


def ssh(command, silent=False):
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    if silent:
        return ssh_stdin, ssh_stdout, ssh_stderr
    for name, stream in zip(["stdin", "stdout", "stderr"], [ssh_stdin, ssh_stdout, ssh_stderr]):
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


def clear_dir(remote_path):  # ToDo currently not working
    return
    if remote_path[-1] != '/':
        remote_path += '/'
    ssh = createSSHClient(rpi_ip, rpi_user, rpi_password)
    sftp = ssh.open_sftp()
    files_to_remove = sftp.listdir(path=remote_path)
    for file in files_to_remove:
        sftp.remove(remote_path + file)


def sync_project():
    local_dir = '/home/anders/Projects/RaspberryPiTracking/'
    remote_dir = '/home/pi/BallDetector'
    print("Syncing {} to {}".format(local_dir, remote_dir))
    upload_dir(local_dir, remote_dir)


if __name__ == "__main__":
    sync_project()
