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
from threading import Event
import libs.rigstarterlib
from gpiozero import RotaryEncoder, Button
import subprocess

gpio_pins = ["CLK", "DT", "SW"]
selected_sat_idx = 0


def get_range(up, down):
    if up > down:
        return range(down, up)
    else:
        return range(up, down)


def selected_sat(button, done):
    done.set()


def shutdown_raspi(button, lcd):
    lcd.clear()
    lcd.write_string(f"shutting down")
    subprocess.run(["sudo", "poweroff"])


def select_sat(rotary, lcd):
    global selected_sat_idx
    selected_sat_idx = rotary.steps
    lcd.clear()
    lcd.write_string("SATELLITE LIST")
    lcd.crlf()
    lcd.crlf()
    lcd.write_string(
        f"{SAT_LIST[selected_sat_idx]['satname']} - {SAT_LIST[selected_sat_idx]['down_mode']}".ljust(
            20, " "
        )
    )
    lcd.crlf()
    if SAT_LIST[selected_sat_idx]["down_mode"] == "FM":
        lcd.write_string(SAT_LIST[selected_sat_idx]["tone"].ljust(20, " "))
    else:
        lcd.write_string("No Tone".ljust(20, " "))


def tuneup(rotary, config, sat_down_range, sat_up_range):
    global rit
    global button
    global current_down
    global current_up
    nextfrequp = current_up
    nextfreqdown = current_down
    if button.is_pressed:
        nextfrequp -= rotary.steps * config["rotary_step"]
    else:
        nextfrequp -= rotary.steps * config["rotary_step"]
        nextfreqdown += rotary.steps * config["rotary_step"]
    print(f"uprange{sat_up_range}")
    print(f"uplink: {nextfrequp}")

    print(f"down range{sat_down_range}")
    print(f"downlink: {nextfreqdown}")
    print(f"step: {rotary.steps}")
    print(nextfreqdown in sat_down_range)
    print(nextfrequp in sat_up_range)
    if nextfreqdown in sat_down_range and nextfrequp in sat_up_range:
        current_down = nextfreqdown
        current_up = nextfrequp


done = Event()
lcd = init_lcd()

with open("config/config.json", "r") as f:
    config = json.load(f)
button = Button(config["gpio_pins"]["SW"], hold_time=3)
# button.when_held = lambda: shutdown_raspi(button, lcd)
libs.rigstarterlib.init_rigs(config, lcd, button)
rotary = RotaryEncoder(
    config["gpio_pins"]["CLK"],
    config["gpio_pins"]["DT"],
    max_steps=len(SAT_LIST),
    wrap=True,
)

rotary.when_rotated = lambda: select_sat(rotary, lcd)
button.when_pressed = lambda: selected_sat(button, done)


if config["enable_radios"]:
    rig_up = rigctllib.RigCtl(config["rig_up_config"])
    rig_down = rigctllib.RigCtl(config["rig_down_config"])
selected_sat_idx = 0
lcd.clear()
lcd.write_string("rotate knob to select a satellite")
from_zone = tz.gettz("UTC")
to_zone = tz.gettz(config["timezone"])


done.wait()

print(f"selected sat {SAT_LIST[selected_sat_idx]['satname']}")


SELECTED_SAT = SAT_LIST[selected_sat_idx]

try:
    update_tles(config["sat_url"])
except:
    print("error downloading tles")

sat = get_tles(SELECTED_SAT["satname"])

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
rotary.when_rotated = lambda: tuneup(rotary, config, sat_down_range, sat_up_range)

rit = 0
while True:
    obs.date = datetime.datetime.utcnow()
    satellite.compute(obs)
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
        rit,
    )
