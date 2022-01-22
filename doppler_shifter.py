#%%
from time import sleep
from libs.satlib import *
from libs.lcdlib import *
from libs.rigstarterlib import log_msg, init_rigs
from libs.gpslib import poll_gps
import ephem
from dateutil import tz
from sys import platform
from RPLCD import i2c
import Hamlib
from libs.rigstarterlib import reset_rig
import time
import json
from libs.satlib import *
from libs.lcdlib import *
import json

try:
    import RPi.GPIO as GPIO
except:
    import Mock.GPIO as GPIO
from threading import Event, Thread
import multiprocessing
from gpiozero import RotaryEncoder, Button
import subprocess
import logging
import os

DEBUG = bool(os.getenv("DEBUG", False))
logFormatter = logging.Formatter(
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
)

RIG_MODES = {
    "FM": Hamlib.RIG_MODE_FM,
    "AM": Hamlib.RIG_MODE_AM,
    "USB": Hamlib.RIG_MODE_USB,
    "LSB": Hamlib.RIG_MODE_LSB,
}
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("./doppler_shifter.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

gpio_pins = ["CLK", "DT", "SW"]

with open("config/config.json", "r") as f:
    config = json.load(f)
with open("config/satlist.json", "r") as f:
    SAT_LIST = json.load(f)
button = Button(config["gpio_pins"]["SW"], hold_time=5)
Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

rig_up = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
rig_down = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)


def get_range(up, down):
    if up > down:
        return range(down, up + 1)
    else:
        return range(up, down + 1)


def selected_sat(button, done):
    done.set()


def shutdown_raspi(button, lcd):
    lcd.clear()
    lcd.write_string(f"shutting down")
    subprocess.run(["sudo", "poweroff"])


def tune_lock_switch(button, ns):
    if ns.tune_lock:
        ns.tune_lock = False
    else:
        ns.diff
        ns.tune_lock = True
        SAT_LIST[ns.selected_sat_idx]["saved_uplink_diff"] = ns.diff
        with open("config/satlist.json", "w") as f:
            json.dump(SAT_LIST, f, indent=4)


def exit_loop(button, ns):
    ns.run_loop = False
    logger.warning("button held")


def select_sat(rotary, lcd, ns):
    lcd.clear()
    ns.selected_sat_idx = rotary.steps
    # 1st line
    line1 = f"{SAT_LIST[ns.selected_sat_idx]['display_name']}"
    lcd.write_string(line1)
    lcd.crlf()
    # 2nd line
    line2 = f"BCN {int(SAT_LIST[ns.selected_sat_idx].get('beacon','0')):,.0f}".replace(
        ",", "."
    )
    lcd.write_string(line2)
    lcd.crlf()

    if SAT_LIST[ns.selected_sat_idx]["down_mode"] == "FM":
        line3 = f"FM {SAT_LIST[ns.selected_sat_idx]['tone'].ljust(20, ' ')}"
    else:
        line3 = "Linear"
    lcd.write_string(line3)
    ns.run_loop = True


def handle_rig_error(rig, side):
    while rig.error_status != 0:
        rig.close()
        if "localhost" in rig.get_conf("rig_pathname"):
            reset_rig(side)
            time.sleep(3)
        rig.open()
        if rig.error_status == 0:
            break


def sat_loop(
    obs, satellite, config, sat_up_range, sat_down_range, lcd, SELECTED_SAT, ns
):
    global rig_up
    global rig_down
    while rig_down.error_status != 0:
        rig_down.open()
    while rig_up.error_status != 0:
        rig_up.open()
    while ns.run_loop:
        obs.date = datetime.datetime.utcnow()
        satellite.compute(obs)
        alt = str(satellite.alt).split(":")[0]
        az = str(satellite.az).split(":")[0]
        shift_down = get_doppler_shift(ns.current_down, satellite.range_velocity)
        shift_up = get_doppler_shift(ns.current_up, satellite.range_velocity)
        shifted_up = get_shifted(ns.current_up, shift_up, "up")
        shifted_down = get_shifted(ns.current_down, shift_down, "down")
        rf_level = 0
        if config["enable_radios"]:
            if rig_up.error_status == 0:
                rig_up.set_freq(Hamlib.RIG_VFO_CURR, shifted_up)
                rf_level = int(rig_up.get_level_f(Hamlib.RIG_LEVEL_RFPOWER) * 100)
            else:
                logger.warning("rigup has errors")
                handle_rig_error(rig_up, "up")
            if rig_down.error_status == 0:
                rig_down.set_freq(Hamlib.RIG_VFO_CURR, shifted_down)
            else:
                logger.warning("rigdown has errors")
                handle_rig_error(rig_down, "down")

            # rig_up.set_split_freq(shifted_up)
            # rig_up.set_vfo("VFOB")
            # rig_up.set_frequency(shifted_up)
            # rig_up.set_vfo("VFOB")
        # try:
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


def tune_vfo(rotary, config, sat_down_range, sat_up_range, sign, ns):

    nextfrequp = ns.current_up
    nextfreqdown = ns.current_down
    if not ns.tune_lock:
        ns.diff += sign * config["rotary_step"]
        rootLogger.warning(f"uplink freq diff is {ns.diff}")
        nextfrequp -= sign * config["rotary_step"]
    else:
        nextfrequp -= sign * config["rotary_step"]
        nextfreqdown += sign * config["rotary_step"]
    rootLogger.warning(f"uprange{sat_up_range}")
    rootLogger.warning(f"uplink: {nextfrequp}")

    rootLogger.warning(f"down range{sat_down_range}")
    rootLogger.warning(f"downlink: {nextfreqdown}")
    rootLogger.warning(f"step: {sign}")
    rootLogger.warning(nextfreqdown in sat_down_range)
    rootLogger.warning(nextfrequp in sat_up_range)
    ns.current_down = nextfreqdown
    ns.current_up = nextfrequp


def main():
    global rig_up
    global rig_down
    global RIG_MODES
    manager = multiprocessing.Manager()
    ns = manager.Namespace()

    lcd = init_lcd()

    lat, lon, ele = poll_gps()

    # override default coordinates with gps
    if lat != "n/a" and lon != "n/a" and ele != "n/a":
        config["observer_conf"]["lon"] = str(lon)
        config["observer_conf"]["lat"] = str(lat)
        config["observer_conf"]["ele"] = ele
        log_msg("setting gps coordinates from radio", lcd, rootLogger)
    else:
        log_msg(
            "cannot read gps coordinates from radio, using default", lcd, rootLogger
        )
    ns.run_loop = True

    ns.selected_sat_idx = 0
    ns.diff = 0
    if config["enable_radios"]:
        rig_up, rig_down = init_rigs(config, lcd, button, rig_up, rig_down)

    while True:
        with open("config/satlist.json", "r") as f:
            ns.SAT_LIST = json.load(f)
        rootLogger.warning("entering main loop")
        done = Event()
        rotary = RotaryEncoder(
            config["gpio_pins"]["CLK"],
            config["gpio_pins"]["DT"],
            max_steps=len(SAT_LIST) - 1,
            wrap=True,
        )

        rotary.when_rotated = lambda: select_sat(rotary, lcd, ns)
        button.when_pressed = lambda: selected_sat(button, done)
        button.when_held = lambda: exit_loop(button, ns)

        log_msg("rotate knob to select a satellite", lcd, rootLogger)
        # from_zone = tz.gettz("UTC")
        # to_zone = tz.gettz(config["timezone"])

        if not DEBUG:
            done.wait()

        rootLogger.warning(
            f"selected sat {SAT_LIST[ns.selected_sat_idx]['display_name']}"
        )

        SELECTED_SAT = SAT_LIST[ns.selected_sat_idx]

        sat = get_tles(SELECTED_SAT["name"])
        ns.SAT_LIST = SAT_LIST
        ns.SELECTED_SAT = SELECTED_SAT
        satellite = ephem.readtle(
            sat[0], sat[1], sat[2]
        )  # create ephem object from tle information

        obs = ephem.Observer()  # recreate Oberserver with current time
        obs.lon = config["observer_conf"]["lon"]
        obs.lat = config["observer_conf"]["lat"]
        obs.elevation = config["observer_conf"]["ele"]

        if isinstance(rig_down, Hamlib.Rig) and isinstance(rig_up, Hamlib.Rig):
            while rig_down.error_status != 0:
                rig_down.open()
            while rig_up.error_status != 0:
                rig_up.open()

            if SELECTED_SAT["down_mode"] == "FM":
                if config["rig_down_config"]["rig_name"] == "TH-D74":
                    rig_down.set_vfo(Hamlib.RIG_VFO_SUB)
                    rig_down.set_level(Hamlib.RIG_LEVEL_SQL, 0.0)
                    rig_down.set_ts(Hamlib.RIG_VFO_SUB, 5000)

                rig_down.set_mode(RIG_MODES[SELECTED_SAT["down_mode"]])
                if SELECTED_SAT["tone"] == "0.0":
                    rig_up.set_func(Hamlib.RIG_FUNC_TONE, 0)
                else:
                    rig_up.set_func(Hamlib.RIG_FUNC_TONE, 1)
                    rig_up.set_ctcss_tone(
                        Hamlib.RIG_VFO_MAIN, int(SELECTED_SAT["tone"].replace(".", ""))
                    )
            else:
                rig_down.set_mode(RIG_MODES[SELECTED_SAT["down_mode"]])
                if config["rig_down_config"]["rig_name"] == "TH-D74":
                    rig_down.set_vfo(Hamlib.RIG_VFO_SUB)
                    rig_down.set_rptr_offs(Hamlib.RIG_VFO_B, 0)
                    rig_down.set_ts(Hamlib.RIG_VFO_SUB, 100)

            rig_up.set_mode(RIG_MODES[SELECTED_SAT["up_mode"]])

        sat_down_range = get_range(SELECTED_SAT["down_start"], SELECTED_SAT["down_end"])
        sat_up_range = get_range(SELECTED_SAT["up_start"], SELECTED_SAT["up_end"])
        ns.current_down = SELECTED_SAT["down_center"]
        ns.current_up = SELECTED_SAT["up_center"] + SELECTED_SAT.get(
            "saved_uplink_diff", 0
        )

        rotary.close()
        rotary = RotaryEncoder(
            config["gpio_pins"]["CLK"],
            config["gpio_pins"]["DT"],
            max_steps=1,
            wrap=False,
        )
        rotary.when_rotated_clockwise = lambda: tune_vfo(
            rotary, config, sat_down_range, sat_up_range, -1, ns
        )
        rotary.when_rotated_counter_clockwise = lambda: tune_vfo(
            rotary, config, sat_down_range, sat_up_range, +1, ns
        )
        ns.tune_lock = True
        button.when_pressed = lambda: tune_lock_switch(button, ns)
        try:
            loop_thread = Thread(
                target=sat_loop,
                args=(
                    obs,
                    satellite,
                    config,
                    sat_up_range,
                    sat_down_range,
                    lcd,
                    SELECTED_SAT,
                    ns,
                ),
            )
            loop_thread.start()
            loop_thread.join()
            rotary.close()
        except Exception as e:
            rootLogger.error(f"Exception error {e}")


if __name__ == "__main__":
    main()
