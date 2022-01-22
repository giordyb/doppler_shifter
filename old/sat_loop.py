from libs.satlib import get_doppler_shift, get_shifted
import datetime
import logging
from libs.lcdlib import *
from libs.rigstarterlib import reset_rig
import os

logger = logging.getLogger(__name__)


def sat_loop(
    obs, satellite, config, sat_up_range, sat_down_range, lcd, SELECTED_SAT, ns
):
    rig_up = ns.rig_up
    rig_down = ns.rig_down

    while ns.run_loop:

        obs.date = datetime.datetime.utcnow()
        satellite.compute(obs)
        alt = str(satellite.alt).split(":")[0]
        az = str(satellite.az).split(":")[0]
        shift_down = get_doppler_shift(ns.current_down, satellite.range_velocity)
        shift_up = get_doppler_shift(ns.current_up, satellite.range_velocity)
        shifted_down = get_shifted(ns.current_down, shift_down, "down")
        shifted_up = get_shifted(ns.current_up, shift_up, "up")
        rf_level = 0
        if config["enable_radios"]:
            try:
                rig_up.set_vfo("VFOA")
                rig_up.set_frequency(shifted_up)
                rf_level = int(rig_up.get_rfpower())

                # rig_up.set_split_freq(shifted_up)
                # rig_up.set_vfo("VFOB")
                # rig_up.set_frequency(shifted_up)
                # rig_up.set_vfo("VFOB")
            except Exception as ex:
                logger.error(f"cannot set frequency on uplink {ex}")
                reset_rig("up")
            # try:
            rig_down.set_frequency(shifted_down)
            # except Exception as ex:
            #    logger.error(f"cannot set frequency on downlink {ex}")
            #    reset_rig("down")

        write_lcd_loop(
            lcd,
            ns.current_up,
            ns.current_down,
            shifted_up,
            shifted_down,
            shift_up,
            shift_down,
            SELECTED_SAT,
            sat_up_range,
            sat_down_range,
            alt,
            az,
            ns.tune_lock,
            ns.diff,
            rf_level,
        )
