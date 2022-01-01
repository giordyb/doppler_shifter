#%%
import datetime
import ephem
from dateutil import tz
import libs.rigctllib as rigctllib
from sys import platform
from RPLCD import i2c
from config.satlist import SAT_LIST
import json
from libs.satlib import *
from libs.lcdlib import *
import RPi.GPIO as GPIO
from threading import Event, Thread
import libs.rigstarterlib
from gpiozero import RotaryEncoder, Button
import subprocess
import time
import logging
from libs.gpslib import poll_gps

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
selected_sat_idx = 0


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


def exit_loop():
    global run_loop
    run_loop = False


def select_sat(rotary, lcd):
    global selected_sat_idx
    selected_sat_idx = rotary.steps
    lcd.clear()
    lcd.write_string(SAT_LIST[selected_sat_idx]["display_name"])
    lcd.crlf()
    lcd.write_string(
        f"BCN {int(SAT_LIST[selected_sat_idx].get('beacon','0')):,.0f}".replace(
            ",", "."
        ).ljust(20, " ")
    )

    lcd.crlf()
    if SAT_LIST[selected_sat_idx]["down_mode"] == "FM":
        lcd.write_string(f"FM {SAT_LIST[selected_sat_idx]['tone'].ljust(20, ' ')}")
    else:
        lcd.write_string("Linear")


def tune_vfo(rotary, config, sat_down_range, sat_up_range, sign):
    global rit
    global button
    global current_down
    global current_up
    nextfrequp = current_up
    nextfreqdown = current_down
    if button.is_pressed:
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
    # if nextfreqdown in sat_down_range and nextfrequp in sat_up_range:
    current_down = nextfreqdown
    current_up = nextfrequp


def sat_loop(obs, satellite, config, sat_up_range, sat_down_range):
    global rig_up
    global rig_down
    global current_up
    global current_down
    global run_loop
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
            rig_up.set_frequency(shifted_up)
            rig_down.set_frequency(shifted_down)

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


lcd = init_lcd()

with open("config/config.json", "r") as f:
    config = json.load(f)
lat, lon, ele = poll_gps(rootLogger)

# override default coordinates with gps
if lat != "n/a" and lon != "n/a" and ele != "n/a":
    config["observer_conf"]["lon"] = str(lon)
    config["observer_conf"]["lat"] = str(lat)
    config["observer_conf"]["ele"] = ele
    rootLogger.warning("setting gps coordinates")
else:
    rootLogger.warning("cannot read gps coordinates, using default")


button = Button(config["gpio_pins"]["SW"], hold_time=20)
button.when_held = exit_loop
try:
    update_tles(config["sat_url"])
    lcd.clear()
    lcd.write_string("successfully downloaded tles")
    time.sleep(3)
    rootLogger.warning("successfully downloaded tles")
except:
    lcd.clear()
    lcd.write_string("error downloading tles")
    time.sleep(3)
    rootLogger.warning("error downloading tles")


if config["enable_radios"]:
    libs.rigstarterlib.init_rigs(config, lcd, button)
    rig_up = rigctllib.RigCtl(config["rig_up_config"])
    rig_down = rigctllib.RigCtl(config["rig_down_config"])

while True:
    rootLogger.warning("entering main loop")
    done = Event()
    rotary = RotaryEncoder(
        config["gpio_pins"]["CLK"],
        config["gpio_pins"]["DT"],
        max_steps=len(SAT_LIST) - 1,
        wrap=True,
    )
    selected_sat_idx = 0

    rotary.when_rotated = lambda: select_sat(rotary, lcd)
    button.when_pressed = lambda: selected_sat(button, done)

    lcd.clear()
    lcd.write_string("rotate knob to select a satellite")
    rootLogger.warning("rotate knob to select a satellite")
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz(config["timezone"])

    done.wait()

    rootLogger.warning(f"selected sat {SAT_LIST[selected_sat_idx]['display_name']}")

    SELECTED_SAT = SAT_LIST[selected_sat_idx]

    sat = get_tles(SELECTED_SAT["name"])

    satellite = ephem.readtle(
        sat[0], sat[1], sat[2]
    )  # create ephem object from tle information

    obs = ephem.Observer()  # recreate Oberserver with current time
    obs.lon = config["observer_conf"]["lon"]
    obs.lat = config["observer_conf"]["lat"]
    obs.elevation = config["observer_conf"]["ele"]

    if config["enable_radios"]:
        rig_down.set_mode(mode=SELECTED_SAT["down_mode"])
        rig_up.set_mode(mode=SELECTED_SAT["up_mode"])

    sat_down_range = get_range(SELECTED_SAT["down_start"], SELECTED_SAT["down_end"])
    sat_up_range = get_range(SELECTED_SAT["up_start"], SELECTED_SAT["up_end"])
    current_down = SELECTED_SAT["down_center"]
    current_up = SELECTED_SAT["up_center"]

    rotary.close()
    rotary = RotaryEncoder(
        config["gpio_pins"]["CLK"], config["gpio_pins"]["DT"], max_steps=1, wrap=False
    )
    rotary.when_rotated_clockwise = lambda: tune_vfo(
        rotary, config, sat_down_range, sat_up_range, -1
    )
    rotary.when_rotated_counter_clockwise = lambda: tune_vfo(
        rotary, config, sat_down_range, sat_up_range, +1
    )

    run_loop = True
    try:
        loop_thread = Thread(
            target=sat_loop, args=(obs, satellite, config, sat_up_range, sat_down_range)
        )
        loop_thread.start()
        loop_thread.join()
        rotary.close()
    except Exception as e:
        rootLogger.error(f"Exception error {e}")
