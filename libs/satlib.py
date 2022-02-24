import urllib.request
import logging
import os
import shutil
import datetime
import json
import ephem
from pathlib import Path
from .gpslib import poll_gps

TLE_FILE = "config/tles.txt"

logger = logging.getLogger(__name__)


def get_satellite(selected_sat):
    sat = get_tles(selected_sat["name"])
    return ephem.readtle(sat[0], sat[1], sat[2])


def load_conf(configpath):
    print(f"loding config {configpath}")
    with open(configpath, "r") as f:
        return json.load(f)


def save_conf(configpath, CONFIG):
    print(f"saving config {configpath}")
    with open(configpath, "w") as f:
        json.dump(CONFIG, f, indent=4)


def get_sat_list():
    with open("config/satlist.json", "r") as f:
        return json.load(f)


def get_tles(sat_name):
    logger.warning(f"getting tles for: {sat_name}")
    try:
        with open(TLE_FILE, "r") as f:
            sat_tle = f.readlines()
            tles = [item.strip() for item in sat_tle]
            tles = [
                (tles[i], tles[i + 1], tles[i + 2]) for i in xrange(0, len(tles) - 2, 3)
            ]
            sat = [x for x in tles if x[0] == sat_name][0]

            return sat
    except Exception as ex:
        logger.error(f"cannot find sat in tle file {ex}")


# TLE Kepler elements
def xrange(x, y, z):
    return iter(range(x, y, z))


def download_tle(sat_url):
    with open(TLE_FILE + ".temp", "w") as f:
        f.write(urllib.request.urlopen(sat_url).read().decode())
    print(f"downloading tles from {sat_url}")
    file_size = os.path.getsize(TLE_FILE + ".temp")
    if file_size > 0:
        shutil.copy(TLE_FILE + ".temp", TLE_FILE)
        return True
    else:
        return False


def update_tles(sat_url):
    path = Path(TLE_FILE)
    if path.is_file():
        tle_timediff = datetime.datetime.now() - datetime.datetime.fromtimestamp(
            os.stat(TLE_FILE).st_ctime
        )
        if tle_timediff > datetime.timedelta(hours=12):
            try:
                result = download_tle(sat_url)
            except:
                result = False
        else:
            result = False
    else:
        result = download_tle(sat_url)

    return result


def get_doppler_shift(frequency, velocity):
    c = 299792458.0  # m/s

    # return velocity / 299792458.0 * frequency
    return int(c / (c + velocity) * frequency - frequency)


def get_shifted(freq, doppler, side):
    if side == "up":
        return int(freq - doppler)
    elif side == "down":
        return int(freq + doppler)


def get_observer(CONFIG):
    lat, lon, ele = poll_gps()
    obs = ephem.Observer()  # recreate Oberserver with current time
    if lat != "n/a" and lon != "n/a" and ele != "n/a":
        obs.lon = lon
        obs.lat = lat
        obs.elevation = ele
    else:
        obs.lon = CONFIG["observer_conf"]["lon"]
        obs.lat = CONFIG["observer_conf"]["lat"]
        obs.elevation = CONFIG["observer_conf"]["ele"]
    return obs
