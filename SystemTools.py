import os
from time import sleep
from datetime import timedelta


def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = int(float(f.readline().split()[0]))
    return uptime_seconds


def get_core_temp():
    temp = os.popen("vcgencmd measure_temp").readline()  # TODO faster to read from /sys/class/thermal/thermal_zone0/temp
    return float(temp.replace("temp=", "").replace("'C", ""))


def get_acquire_fps(video, wait_time=5):
    pre_idx = video.ring_buffer.current_frame_idx()
    sleep(wait_time)
    post_idx = video.ring_buffer.current_frame_idx()
    return (post_idx - pre_idx) / wait_time


def get_analysis_fps(perioddic_saver, wait_time=5):
    pre_count = perioddic_saver.counter
    sleep(wait_time)
    post_count = perioddic_saver.counter
    return (post_count - pre_count) / wait_time


def get_system_info(video=None, perioddic_saver=None):
    system_info = {'Uptime': str(timedelta(seconds=get_uptime())),
                   "Core temperature": get_core_temp()}
    if video is not None:
        system_info.update({'Acquire FPS': get_acquire_fps(video)})
    if perioddic_saver is not None:
        system_info.update({'Analysis FPS': get_analysis_fps(perioddic_saver)})

    return system_info
