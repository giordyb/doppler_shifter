import pygame_menu
import os
import subprocess
import logging
from .satlib import get_doppler_shift, get_shifted
import datetime
import time

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


def configure_rig(rig, rignum, CONFIG):
    rig.set_conf("retry", "5")

    rig_pathname = (
        f"{CONFIG['rigs'][rignum]['hostname']}:{CONFIG['rigs'][rignum]['port']}"
    )
    rig.set_conf(
        "rig_pathname",
        rig_pathname,
    )
    rig.rig_name = CONFIG["rigs"][rignum]["rig_name"]
    rig.vfo_name = CONFIG["rigs"][rignum]["vfo_name"]
    rig.rig_num = rignum
    rig.tone = 0

    rig.open()
    if rig.rig_name == "SDRPP":
        rig.state.vfo_opt = 0
    return rig


def create_slider(CURRENT_SAT_CONFIG, side):
    slider = pygame_menu.widgets.RangeSlider(
        title="",
        default_value=CURRENT_SAT_CONFIG[f"{side}_center"],
        range_values=(
            CURRENT_SAT_CONFIG[f"{side}_start"],
            CURRENT_SAT_CONFIG[f"{side}_end"],
        ),
        increment=1,
        value_format=lambda x: f"{x:,.0f}".replace(",", "."),
        cursor=None,
        range_width=300,
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
    ele = str(CURRENT_SAT_OBJECT.alt).split(":")[0]
    az = str(CURRENT_SAT_OBJECT.az).split(":")[0]
    shift_down = get_doppler_shift(CURRENT_DOWN_FREQ, CURRENT_SAT_OBJECT.range_velocity)
    shift_up = get_doppler_shift(CURRENT_UP_FREQ, CURRENT_SAT_OBJECT.range_velocity)
    shifted_down = get_shifted(CURRENT_DOWN_FREQ, shift_down, "down")
    shifted_up = get_shifted(CURRENT_UP_FREQ, shift_up, "up")
    return az, ele, shift_down, shift_up, shifted_down, shifted_up
