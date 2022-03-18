import pygame_menu
import os
import subprocess
import logging
from .satlib import get_doppler_shift, get_shifted
import datetime
import time
import ephem

logger = logging.getLogger(__name__)


def shutdown():
    subprocess.run(["sudo", "shutdown", "-h", "now"])


def configure_rot(rot, CONFIG):
    rot.set_conf("retry", "5")

    rot_pathname = f"{CONFIG['rotator']['hostname']}:{CONFIG['rotator']['port']}"
    rot.set_conf(
        "rot_pathname",
        rot_pathname,
    )
    rot.open()
    return rot


def create_slider(CURRENT_SAT_CONFIG, side):
    if CURRENT_SAT_CONFIG["up_mode"] == "FM":
        range_vals = (0, 1)
        default = 0
    else:
        range_vals = (
            CURRENT_SAT_CONFIG[f"{side}_start"],
            CURRENT_SAT_CONFIG[f"{side}_end"],
        )
        default = CURRENT_SAT_CONFIG[f"{side}_center"]
    slider = pygame_menu.widgets.RangeSlider(
        title=side.upper()[0],
        default_value=default,
        range_values=range_vals,
        increment=1,
        value_format=lambda x: f"{x:,.0f}".replace(",", "."),
        cursor=None,
        range_width=450,
    )
    slider.is_selectable = False
    slider.readonly = True

    return slider


def restart_rig(side):
    logger.warning(f"restaring rig {side}")
    if not os.getenv("DEBUG", False):
        logger.warning(f"resetting rig {side}")
        subprocess.run(["sudo", "systemctl", "stop", f"rig{side}"])
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "start", f"rig{side}"])


def recalc_shift_and_pos(
    observer, CURRENT_SAT_OBJECT, CURRENT_UP_FREQ, CURRENT_DOWN_FREQ
):
    observer.date = datetime.datetime.utcnow()
    CURRENT_SAT_OBJECT.compute(observer)
    # ele = str(CURRENT_SAT_OBJECT.alt).split(":")[0]
    ele = CURRENT_SAT_OBJECT.alt
    # az = str(CURRENT_SAT_OBJECT.az).split(":")[0]
    az = CURRENT_SAT_OBJECT.az
    shift_down = get_doppler_shift(CURRENT_DOWN_FREQ, CURRENT_SAT_OBJECT.range_velocity)
    shift_up = get_doppler_shift(CURRENT_UP_FREQ, CURRENT_SAT_OBJECT.range_velocity)
    shifted_down = get_shifted(CURRENT_DOWN_FREQ, shift_down, "down")
    shifted_up = get_shifted(CURRENT_UP_FREQ, shift_up, "up")

    next_pass = observer.next_pass(CURRENT_SAT_OBJECT)
    aos = ephem.localtime(next_pass[0]) - datetime.datetime.now()
    los = ephem.localtime(next_pass[4]) - datetime.datetime.now()
    return az, ele, shift_down, shift_up, shifted_down, shifted_up, aos, los
