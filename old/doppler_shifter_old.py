#%%
import datetime
import ephem
import time
import urllib.request
from dateutil import tz
import libs.rigctllib as rigctllib
from sys import platform
from RPLCD import i2c
from config.satlist import SAT_LIST
import json
from libs.satlib import *
from libs.lcdlib import *
import RPi.GPIO as GPIO

gpio_pins = ["CLK", "DT", "SW"]
selected_sat_idx = 0
from gpiozero import RotaryEncoder, Button


def gpio_remove_event_detect():
    for pin in gpio_pins:
        GPIO.remove_event_detect(config["gpio_pins"][pin])


def gpio_init(config):
    GPIO.setmode(GPIO.BCM)
    for pin in ["CLK", "DT", "SW"]:
        # set up the GPIO events on those pins
        GPIO.setup(config["gpio_pins"][pin], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def rotated_satsel(channel):
    global selected_sat_idx
    CLKState = GPIO.input(config["gpio_pins"]["CLK"])
    DTState = GPIO.input(config["gpio_pins"]["DT"])
    if CLKState == 0 and DTState == 1:
        if selected_sat_idx + 1 in range(0, len(SAT_LIST)):
            selected_sat_idx += 1
    elif CLKState == 1 and DTState == 0:
        if selected_sat_idx - 1 in range(0, len(SAT_LIST)):
            selected_sat_idx -= 1
    print(f"selected sat idx {selected_sat_idx}")


def rotated_freqmenu(channel):
    global current_up
    global current_down

    CLKState = GPIO.input(config["gpio_pins"]["CLK"])
    DTState = GPIO.input(config["gpio_pins"]["DT"])
    if CLKState == 0 and DTState == 1:
        if current_down + config["rotary_step"] in sat_range:
            current_down += config["rotary_step"]
            current_up -= config["rotary_step"]
    elif CLKState == 1 and DTState == 0:
        if current_down - config["rotary_step"] in sat_range:
            current_down -= config["rotary_step"]
            current_up += config["rotary_step"]

    print(f"current down {current_down} - current up {current_up}")


def clicked_satsel(channel):
    global sat_selection_menu
    sat_selection_menu = False


def clicked_freqmenu(channel):
    pass


def main():
    with open("config/config.json", "r") as f:
        config = json.load(f)
    rotary = RotaryEncoder(config["gpio_pins"]["CLK"], config["gpio_pins"]["DT"])

    if config["enable_radios"]:
        rig_up = rigctllib.RigCtl(config["rig_up_config"])
        rig_down = rigctllib.RigCtl(config["rig_down_config"])
    selected_sat_idx = 0
    lcd = init_lcd()
    lcd.clear()
    lcd.write_string("starting up")
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz(config["timezone"])

    sat_selection_menu = True

    gpio_init(config)
    GPIO.add_event_detect(CLK, GPIO.FALLING, callback=rotated_satsel, bouncetime=180)
    GPIO.add_event_detect(DT, GPIO.FALLING, callback=rotated_satsel, bouncetime=180)
    GPIO.add_event_detect(SW, GPIO.FALLING, callback=clicked_satsel, bouncetime=150)

    while sat_selection_menu:
        lcd.home()
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

    print(f"selected sat {SAT_LIST[selected_sat_idx]['satname']}")

    SELECTED_SAT = SAT_LIST[selected_sat_idx]

    gpio_remove_event_detect()
    try:
        update_tles(config["sat_url"])
    except:
        print("error downloading tles")
    sat = get_tles(SELECTED_SAT["satname"])

    #%%
    satellite = ephem.readtle(
        sat[0], sat[1], sat[2]
    )  # create ephem object from tle information

    obs = ephem.Observer()  # recreate Oberserver with current time
    obs.lon = config["observer_conf"]["lon"]
    obs.lat = config["observer_conf"]["lat"]
    obs.elevation = config["observer_conf"]["elev"]

    if config["enable_radios"]:
        rig_down.set_mode(mode=SELECTED_SAT["down_mode"])
        rig_up.set_mode(mode=SELECTED_SAT["up_mode"])
    sat_range = range(SELECTED_SAT["down_start"], SELECTED_SAT["down_end"])
    current_down = SELECTED_SAT["down_center"]
    current_up = SELECTED_SAT["up_center"]

    GPIO.add_event_detect(
        config["gpio_pins"]["CLK"],
        GPIO.FALLING,
        callback=rotated_freqmenu,
        bouncetime=180,
    )
    GPIO.add_event_detect(
        config["gpio_pins"]["DT"],
        GPIO.FALLING,
        callback=rotated_freqmenu,
        bouncetime=180,
    )
    GPIO.add_event_detect(
        config["gpio_pins"]["SW"],
        GPIO.FALLING,
        callback=clicked_freqmenu,
        bouncetime=150,
    )

    while True:
        obs.date = datetime.datetime.utcnow()
        satellite.compute(obs)
        shift_down = get_doppler_shift(current_down, satellite.range_velocity)
        shift_up = get_doppler_shift(current_up, satellite.range_velocity)
        shifted_down = get_shifted(current_down, shift_down, "down")
        shifted_up = get_shifted(current_up, shift_up, "up")

        if enable_radios:
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


if __name__ == "__main__":
    main()
