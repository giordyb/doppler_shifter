from libs.satlib import *
import datetime
import logging
from libs.lcdlib import *
from rigstarterlib import reset_rig

logger = logging.getLogger(__name__)


def sat_loop(
    obs,
    satellite,
    config,
    sat_up_range,
    sat_down_range,
    rig_up,
    rig_down,
    current_up,
    current_down,
    run_loop,
    lcd,
    SELECTED_SAT,
):

    while run_loop:
        obs.date = datetime.datetime.utcnow()
        satellite.compute(obs)
        alt = str(satellite.alt).split(":")[0]
        az = str(satellite.az).split(":")[0]
        shift_down = get_doppler_shift(current_down, satellite.range_velocity)
        shift_up = get_doppler_shift(current_up, satellite.range_velocity)
        shifted_down = get_shifted(current_down, shift_down, "down")
        shifted_up = get_shifted(current_up, shift_up, "up")

        if config["enable_radios"]:
            try:
                rig_up.set_frequency(shifted_up)
            except:
                logger.error("cannot set frequency on uplink")
                reset_rig("up")
            try:
                rig_down.set_frequency(shifted_down)
            except:
                logger.error("cannot set frequency on downlink")
                reset_rig("down")

        write_lcd_loop(
            lcd,
            current_up,
            current_down,
            shifted_up,
            shifted_down,
            shift_up,
            shift_down,
            SELECTED_SAT,
            sat_up_range,
            sat_down_range,
            alt,
            az,
        )
        print(f"alt: {alt}, az: {az} range: {satellite.range}")
