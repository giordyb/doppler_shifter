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

gpio_pins = ["CLK", "DT", "SW"]
selected_sat_idx = 0


def get_range(up, down):
    if up > down:
        return range(down, up)
    else:
        return range(up, down)


done = Event()
lcd = init_lcd()


def selected_sat():
    done.set()


7


def select_sat(r):
    global selected_sat_idx
    selected_sat_idx = r.steps
    lcd.clear()
    lcd.write_string("SELECT SATELLITE")
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


with open("config/config.json", "r") as f:
    config = json.load(f)
button = Button(config["gpio_pins"]["SW"])
libs.rigstarterlib.init_rigs(config, lcd, button)
rotor = RotaryEncoder(
    config["gpio_pins"]["CLK"],
    config["gpio_pins"]["DT"],
    max_steps=len(SAT_LIST),
    wrap=True,
)

rotor.when_rotated = select_sat
button.when_pressed = selected_sat


if config["enable_radios"]:
    rig_up = rigctllib.RigCtl(config["rig_up_config"])
    rig_down = rigctllib.RigCtl(config["rig_down_config"])
selected_sat_idx = 0
lcd.clear()
lcd.write_string("rotate to select sat")
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


def tuneup(r):
    global current_down
    global current_up
    global config
    global sat_down_range
    global sat_up_range
    nextfreqdown = current_down + (r.steps * config["rotary_step"])
    nextfrequp = current_up - (r.steps * config["rotary_step"])
    print(f"uprange{sat_up_range}")
    print(f"uplink: {nextfrequp}")

    print(f"down range{sat_down_range}")
    print(f"downlink: {nextfreqdown}")
    print(f"step: {r.steps}")
    print(nextfreqdown in sat_down_range)
    print(nextfrequp in sat_up_range)
    if nextfreqdown in sat_down_range and nextfrequp in sat_up_range:
        current_down = nextfreqdown
        current_up = nextfrequp


rotor.close()
rotor = RotaryEncoder(
    config["gpio_pins"]["CLK"], config["gpio_pins"]["DT"], max_steps=1, wrap=False
)
rotor.when_rotated = tuneup

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
    )
