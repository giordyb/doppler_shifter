import libs.rigctllib
import socket
import time
import subprocess


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


def init_rigs(config, lcd, button):
    for side in ["down", "up"]:
        rig_init = False
        rig = libs.rigctllib.RigCtl(config[f"rig_{side}_config"])
        while rig_init == False:

            try:
                lcd.clear()
                lcd.write_string(
                    f"turn on {side}link rig\n\rand press the rotary\n\rencoder button"
                )
                button.wait_for_press()
                subprocess.run(["sudo", "systemctl", "restart", f"rig{side}"])
                port_ready = 1
                wait_for_port(
                    config[f"rig_{side}_config"]["port"],
                    config[f"rig_{side}_config"]["hostname"],
                    timeout=10,
                )

                change_mode_result = rig.set_mode(mode="FM")
                if change_mode_result == "RPRT 0":

                    lcd.clear()
                    lcd.write_string(f"{side}link rig\n\rstarted")
                    button.wait_for_press()
                    rig_init = True
                else:
                    lcd.clear()
                    lcd.write_string(f"{side}link rig\n\rerror")
                    button.wait_for_press()
                    rig_init = False

            except (ConnectionRefusedError, TimeoutError):
                lcd.clear()
                lcd.write_string(f"error starting\n\r{side}link rig\n\rrigctld service")
                button.wait_for_press()
