import libs.rigctllib
import socket
import time
import subprocess
import os
from libs.satlib import update_tles
import logging

logger = logging.getLogger(__name__)
DEBUG = bool(os.getenv("DEBUG", False))


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


def reset_rig(rig_side):
    if not os.getenv("DEBUG", False):
        subprocess.run(["sudo", "systemctl", "stop", f"rig{rig_side}"])
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "start", f"rig{rig_side}"])


def wait_for_press_wrapper(button):
    if not DEBUG:
        button.wait_for_press()


def init_rigs(config, lcd, button):
    lcd.clear()
    lcd.write_string(f"press rotary encoder\n\rto start")
    logger.warning("press rotary encoder to start")
    wait_for_press_wrapper(button)

    if update_tles(config["sat_url"]):
        if lcd:
            lcd.clear()
            lcd.write_string("successfully downloaded tles")
        logger.warning("successfully downloaded tles")
    else:
        if lcd:
            lcd.clear()
            lcd.write_string("error downloading tles")
        logger.warning("error downloading tles")
    time.sleep(1)

    for side in ["down", "up"]:
        rig_init = False
        rig = libs.rigctllib.RigCtl(config[f"rig_{side}_config"])
        while rig_init == False:
            try:
                lcd.clear()
                lcd.write_string(
                    f"turn on {side}link rig\n\rand press the rotary\n\rencoder button"
                )
                logger.warning(
                    f"turn on {side}link rig\n\rand press the rotary\n\rencoder button"
                )
                wait_for_press_wrapper(button)

                reset_rig(side)
                port_ready = 1
                wait_for_port(
                    config[f"rig_{side}_config"]["port"],
                    config[f"rig_{side}_config"]["hostname"],
                    timeout=10,
                )

                change_mode_result = rig.set_mode(mode="AM")

                lcd.clear()
                if change_mode_result == "RPRT 0":
                    lcd.write_string(f"{side}link rig\n\rstarted")
                    logger.warning(f"{side}link rig\n\rstarted")
                    rig_init = True
                else:
                    lcd.write_string(f"{side}link rig\n\rerror")
                    logger.warning(f"{side}link rig\n\rerror")
                    rig_init = False
                wait_for_press_wrapper(button)

            except (ConnectionRefusedError, TimeoutError):
                lcd.clear()
                lcd.write_string(f"error starting\n\r{side}link rig\n\rrigctld service")
                logger.warning(f"error starting\n\r{side}link rig\n\rrigctld service")
                wait_for_press_wrapper(button)

