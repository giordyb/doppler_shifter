import socket
import time
import subprocess
import os
from libs.satlib import update_tles
import logging
import datetime
from time import sleep
import Hamlib

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
        logger.warning(f"resetting rig {rig_side}")
        subprocess.run(["sudo", "systemctl", "stop", f"rig{rig_side}"])
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "start", f"rig{rig_side}"])


def wait_for_press_wrapper(button):
    if not DEBUG:
        button.wait_for_press()


def init_rigs(config, lcd, button, rig_up, rig_down):
    datestring = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg(
        f"press rotary encoder\n\rto init rigs\n\r{datestring}",
        lcd,
        logger,
    )
    wait_for_press_wrapper(button)
    update_return_code = update_tles(config["sat_url"])
    if update_return_code == 1:
        log_msg("successfully downloaded tles", lcd, logger)
    elif update_return_code == 2:
        log_msg("tles still valid", lcd, logger)
    else:
        log_msg("error downloading tles", lcd, logger)
    time.sleep(1)

    for side in ["down", "up"]:
        logger.warning(f"initializing {side}rig")
        rig_side_config = f"rig_{side}_config"
        rig_pathname = (
            f"{config[rig_side_config]['hostname']}:{config[rig_side_config]['port']}"
        )
        # wait_func = lambda x: wait_for_port(
        #    config[rig_side_config]["port"],
        #    config[rig_side_config]["hostname"],
        #    timeout=5,
        # )
        rig = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
        rig.set_conf(
            "rig_pathname",
            rig_pathname,
        )
        rig.set_conf("retry", "5")

        rig.open()

        # reset_rig(side)

        while rig.error_status != 0:
            try:
                rig.close()
                lcd.clear()
                lcd.write_string(
                    f"turn on {side}link rig\n\rand press the rotary\n\rencoder button"
                )
                logger.warning(
                    f"turn on {side}link rig\n\rand press the rotary\n\rencoder button"
                )
                wait_for_press_wrapper(button)

                reset_rig(side)
                time.sleep(3)
                # if not wait_func(""):
                #    continue

                rig.open()
                if rig.error_status != 0:
                    continue
                rig.set_mode(Hamlib.RIG_MODE_AM)

                if rig.error_status == 0:
                    break
                else:
                    lcd.write_string(f"{side}link rig\n\rerror")
                    logger.warning(f"{side}link rig\n\rerror")
                    wait_for_press_wrapper(button)

            except (ConnectionRefusedError, TimeoutError):
                lcd.clear()
                lcd.write_string(f"error starting\n\r{side}link rig\n\rrigctld service")
                logger.warning(f"error starting\n\r{side}link rig\n\rrigctld service")
                wait_for_press_wrapper(button)
        lcd.clear()
        lcd.write_string(f"{side}link rig\n\rstarted")
        logger.warning(f"{side}link rig\n\rstarted")
        if side == "down":
            rig.open()
            rig_down = rig
        if side == "up":
            rig.open()
            rig_up = rig

        time.sleep(0.5)

    return rig_up, rig_down
