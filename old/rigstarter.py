#%%
import RPi.GPIO as GPIO
from RPLCD import i2c
import json
from gpiozero import RotaryEncoder, Button
import socket

import time
import socket


def wait_for_port(port, host="localhost", timeout=5.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port (int): Port number.
        host (str): Host address on which the port should exist.
        timeout (float): In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError(
                    "Waited too long for the port {} on host {} to start accepting "
                    "connections.".format(port, host)
                ) from ex


def init_lcd():

    lcdmode = "i2c"
    cols = 20
    rows = 4
    charmap = "A00"
    i2c_expander = "PCF8574"
    address = 0x27
    port = 1
    return i2c.CharLCD(
        i2c_expander, address, port=port, charmap=charmap, cols=cols, rows=rows
    )


# main.py
import sys
import subprocess
import libs.rigctllib as rigctllib


with open("config/config.json", "r") as f:
    config = json.load(f)
CLK = 17
DT = 18
SW = 27
clicked = True
lcd = init_lcd()

# %%


def init_rigs():

    for side in ["down", "up"]:
        rig_init = False
        rig = rigctllib.RigCtl(config[f"rig_{side}_config"])
        while rig_init == False:

            try:
                lcd.clear()
                lcd.write_string(f"turn on {side} rig and press button")
                button.wait_for_press()
                subprocess.run(
                    [
                        "sudo",
                        "systemctl",
                        "restart",
                        f"rig{side}",
                    ]
                )
                port_ready = 1
                wait_for_port(
                    config[f"rig_{side}_config"]["port"],
                    config[f"rig_{side}_config"]["hostname"],
                    timeout=10,
                )

                change_mode_result = rig.set_mode(mode="FM")
                if change_mode_result == "RPRT 0":

                    lcd.clear()
                    lcd.write_string(f"rig {side} started")
                    button.wait_for_press()
                    rig_init = True
                else:
                    lcd.clear()
                    lcd.write_string(f"rig {side} error")
                    button.wait_for_press()
                    rig_init = False

            except (ConnectionRefusedError, TimeoutError):
                lcd.clear()
                lcd.write_string(f"error starting rig {side} rigctld service")
                button.wait_for_press()
