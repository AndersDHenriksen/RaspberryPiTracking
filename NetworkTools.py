from uuid import getnode
import socket
import struct
from time import sleep
import os

# connection_string = "eurt=setirWyrter?tset/ten.bdognom.pcg.van5q-0retsulc-pcg@del2ebbutS:naMkcarT//:vrs+bdognom"
connection_string = "eurt=setirWyrter&nimda=ecruoShtua&0-drahs-0retsulc-pcg=teSacilper&eurt=lss?tset/71072:ten.bdognom.pcg.van5q-20-00-drahs-0retsulc-pcg,71072:ten.bdognom.pcg.van5q-10-00-drahs-0retsulc-pcg,71072:ten.bdognom.pcg.van5q-00-00-drahs-0retsulc-pcg@del2ebbutS:naMkcarT//:bdognom"


# https://stackoverflow.com/questions/2761829/python-get-default-gateway-for-a-local-interface-ip-address-in-linux/2761952
def get_default_gateway_linux():
    """Read the default gateway directly from /proc."""
    with open("/proc/net/route") as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue
            return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))


def get_mac_address():
    return getnode()


def get_ip_address(use_internet_route=True):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            ip_connect = "8.8.8.8"
            if not use_internet_route:
                ip_connect = get_default_gateway_linux()
                if ip_connect is None:
                    return None
            s.connect((ip_connect, 80))
        except OSError:
            return None  # No internet
        return s.getsockname()[0]


def get_network_info_collection():
    import pymongo
    client = pymongo.MongoClient(connection_string[::-1])
    networkinfo_collection = client["RaspberryPi"]["NetworkInfo"]
    return networkinfo_collection


def update_network_info(delete_dead_entries=False):
    assert get_ip_address() is not None
    networkinfo_collection = get_network_info_collection()
    for entry in networkinfo_collection.find():
        alive = os.system("ping -c 1 " + entry["Ip"]) == 0
        if not alive and delete_dead_entries:
            networkinfo_collection.remove(entry["_id"])
        elif alive != entry['Alive']:
            entry['Alive'] = alive
            networkinfo_collection.update({'_id': entry["_id"]}, entry, upsert=True)


def upset_network_info():
    mac_address = get_mac_address()
    ip = get_ip_address()
    attempts = 10
    while ip is None and attempts:
        sleep(60)
        attempts -= 1
        ip = get_ip_address()
    assert ip is not None and mac_address is not None
    networkinfo_collection = get_network_info_collection()
    networkinfo = {'MacAddress': mac_address, 'Ip': ip, 'Alive': True}
    networkinfo_collection.update({'MacAddress': mac_address}, networkinfo, upsert=True)


if __name__ == "__main__":
    upset_network_info()