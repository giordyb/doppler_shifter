import urllib.request
import logging
import os
import shutil

TLE_FILE = "config/tles.txt"

logger = logging.getLogger(__name__)


def get_tles(sat_name):
    logger.warning(f"getting tles for: {sat_name}")
    with open(TLE_FILE, "r") as f:
        sat_tle = f.readlines()
        tles = [item.strip() for item in sat_tle]
        tles = [
            (tles[i], tles[i + 1], tles[i + 2]) for i in xrange(0, len(tles) - 2, 3)
        ]
        sat = [x for x in tles if x[0] == sat_name][0]

        return sat


# TLE Kepler elements
def xrange(x, y, z):
    return iter(range(x, y, z))


def update_tles(sat_url):
    try:
        with open(TLE_FILE + ".temp", "w") as f:
            f.write(urllib.request.urlopen(sat_url).read().decode())
        file_size = os.path.getsize(TLE_FILE + ".temp")
        if file_size > 0:
            shutil.copy(TLE_FILE + ".temp", TLE_FILE)
            return True
        else:
            return False
    except:
        return False


def get_doppler_shift(frequency, velocity):
    c = 299792458.0  # m/s

    # return velocity / 299792458.0 * frequency
    return int(c / (c + velocity) * frequency - frequency)


def get_shifted(freq, doppler, side):
    if side == "up":
        return int(freq - doppler)
    elif side == "down":
        return int(freq + doppler)
