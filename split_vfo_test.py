#%%
import libs.rigctllib as rigctllib
import json
import libs.rigstarterlib
import Mock.GPIO as GPIO
from gpiozero import RotaryEncoder, Button
from libs.lcdlib import *
import os

with open("config/config.json", "r") as f:
    config = json.load(f)
from RPLCD import i2c

lcd = init_lcd()
DEBUG = bool(os.getenv("DEBUG", False))

# button = Button(config["gpio_pins"]["SW"], hold_time=5)
# libs.rigstarterlib.init_rigs(config, lcd, button)

#%%

rig_down = rigctllib.RigCtl(config["rig_down_config"])
rig_down.send_custom_cmd("w FT 0\r")

# %%
"""
rig_up = rigctllib.RigCtl(config["rig_up_config"])
rig_up.set_vfo("VFOA")
rig_up.set_frequency(435640000)
rig_up.set_vfo("VFOB")
rig_up.set_frequency(145965000)
rig_up.set_vfo("VFOA")

rig_up.set_mode("USB")
rig_up.set_split_vfo(1, "VFOB")
rig_up.set_split_mode("LSB")
"""
# %%
