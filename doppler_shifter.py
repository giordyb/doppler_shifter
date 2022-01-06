#%%
import libs.rigctllib as rigctllib
from libs.satlib import *
from libs.lcdlib import *
import libs.rigstarterlib
from libs.gpslib import poll_gps
from libs.sat_loop import sat_loop
import ephem
from dateutil import tz
from sys import platform
from RPLCD import i2c

# from config.satlist import SAT_LIST
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
            json.dump(SAT_LIST, f)


def exit_loop(button, ns):
    ns.run_loop = False
    logger.warning("button held")


def select_sat(rotary, lcd, ns):
    ns.selected_sat_idx = rotary.steps
    lcd.clear()
    lcd.write_string(SAT_LIST[ns.selected_sat_idx]["display_name"])
    lcd.crlf()
    lcd.write_string(
        f"BCN {int(SAT_LIST[ns.selected_sat_idx].get('beacon','0')):,.0f}".replace(
            ",", "."
        ).ljust(20, " ")
    )

    lcd.crlf()

    if SAT_LIST[ns.selected_sat_idx]["down_mode"] == "FM":
        lcd.write_string(f"FM {SAT_LIST[ns.selected_sat_idx]['tone'].ljust(20, ' ')}")
    else:
        lcd.write_string("Linear")
    ns.run_loop = True


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

    manager = multiprocessing.Manager()
    ns = manager.Namespace()

    lcd = init_lcd()

    lat, lon, ele = poll_gps(rootLogger)

    # override default coordinates with gps
    if lat != "n/a" and lon != "n/a" and ele != "n/a":
        config["observer_conf"]["lon"] = str(lon)
        config["observer_conf"]["lat"] = str(lat)
        config["observer_conf"]["ele"] = ele
        rootLogger.warning("setting gps coordinates")
    else:
        rootLogger.warning("cannot read gps coordinates, using default")
    ns.run_loop = True
    ns.rig_up = None
    ns.rig_down = None
    ns.selected_sat_idx = 0
    ns.diff = 0
    if config["enable_radios"]:
        libs.rigstarterlib.init_rigs(config, lcd, button)
        ns.rig_up = rigctllib.RigCtl(config["rig_up_config"])
        ns.rig_down = rigctllib.RigCtl(config["rig_down_config"])

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

        if lcd:
            lcd.clear()
            lcd.write_string("rotate knob to select a satellite")
        rootLogger.warning("rotate knob to select a satellite")
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

        if isinstance(ns.rig_down, rigctllib.RigCtl) and isinstance(
            ns.rig_up, rigctllib.RigCtl
        ):
            ns.rig_down.set_mode(mode=SELECTED_SAT["down_mode"])
            # ns.rig_up.set_split_mode(mode=SELECTED_SAT["up_mode"], bandwidth=0)
            ns.rig_up.set_mode(mode=SELECTED_SAT["up_mode"])
            # ns.rig_up.set_split_vfo(1, "VFOB")

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
