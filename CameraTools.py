import numpy as np


@property
def possible_iso_values():
    return np.array([100, 200, 320, 400, 500, 640, 800])  # 100: Gain = 1.84. 800: Gain: 14.72


def get_camera_settings(camera, silent=False):

    important_settings = ["exposure_compensation", "framerate", "iso", "resolution", "shutter_speed"]

    other_settings = ["analog_gain", "awb_gains", "awb_mode", "brightness", "contrast", "digital_gain", "drc_strength",
                      "exposure_mode", "exposure_speed", "hflip", "image_denoise", "meter_mode", "rotation",
                      "saturation", "sensor_mode", "sharpness", "vflip", "video_denoise", "video_stabilization", "zoom"]

    settings_dict = {'important_settings': {s: getattr(camera, s) for s in important_settings},
                         'other_settings': {s: getattr(camera, s) for s in other_settings}}
    if silent:
        return settings_dict
    from pprint import pprint
    pprint(settings_dict, width=1)


def setup_camera(camera, exposure_compensation=None, iso=None):

    assert 25 >= (exposure_compensation or 0) >= -25

    if iso is not None and iso not in possible_iso_values:
        print("ISO valued will be rounded to nearest possible value")

    camera.shutter_speed = 4000
    camera.framerate = 90
    if exposure_compensation is not None:
        camera.exposure_compensation = exposure_compensation
    if iso is not None:
        camera.iso = iso
    camera.resolution = (640, 480)  # Also possible: (1280, 720)
    # Consider setting camera.exposure_mode = 'sports'


def change_pixel_intensity(camera, ratio):

    all_iso_values = possible_iso_values
    exposure_compensation_steps = np.arange(-25, 26)
    exposure_compensation_ratio = (2 ** (1.0 / 6)) ** exposure_compensation_steps

    current_iso_value = camera.iso
    current_exposure_compensation = camera.exposure_compensation

    # Adjust desired ratio if it had 0 exposure compensation
    current_exposure_compensation_ratio = (2 ** (1.0 / 6)) ** current_exposure_compensation
    ratio *= current_exposure_compensation_ratio
    current_exposure_compensation = 0

    # Find best iso then best exposure compensation
    iso_ratios = all_iso_values.astype(np.float) / current_iso_value
    iso_idx = np.abs(iso_ratios - ratio).argmin()
    iso = all_iso_values[iso_idx]
    remaining_ratio = ratio / iso_ratios[iso_idx]
    exposure_compensation_idx = np.abs(exposure_compensation_ratio - remaining_ratio).argmin()
    exposure_compensation = exposure_compensation_steps[exposure_compensation_idx]
    setup_camera(camera, exposure_compensation, iso)
