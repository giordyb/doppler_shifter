import libs.rigctllib
import socket
import time
import subprocess
import os
from libs.satlib import update_tles
import logging
import datetime
from time import sleep

logger = logging.getLogger(__name__)
DEBUG = bool(os.getenv("DEBUG", False))


def log_msg(message, lcd, logger):
    logger.warning(message)
    lcd.clear()
    lcd.write_string(message)
    sleep(0.5)


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
                return False
    return True


def reset_rig(rig_side):
    if not os.getenv("DEBUG", False):
        subprocess.run(["sudo", "systemctl", "stop", f"rig{rig_side}"])
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "start", f"rig{rig_side}"])


def wait_for_press_wrapper(button):
    if not DEBUG:
        button.wait_for_press()


def init_rigs(config, lcd, button):
    datestring = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg(
        f"press rotary encoder\n\rto init rigs\n\r{datestring}",
        lcd,
        logger,
    )
    wait_for_press_wrapper(button)

    if update_tles(config["sat_url"]):
        log_msg("successfully downloaded tles", lcd, logger)
    else:
        log_msg("error downloading tles", lcd, logger)
    time.sleep(1)

    for side in ["down", "up"]:
        wait_func = lambda x: wait_for_port(
            config[f"rig_{side}_config"]["port"],
            config[f"rig_{side}_config"]["hostname"],
            timeout=5,
        )
        rig = libs.rigctllib.RigCtl(config[f"rig_{side}_config"])
        rig_init = wait_func("")
        reset_rig(side)
        while not rig_init:
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
                if not wait_func(""):
                    continue
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
        lcd.clear()
        lcd.write_string(f"{side}link rig\n\rstarted")
        logger.warning(f"{side}link rig\n\rstarted")
        time.sleep(0.5)
