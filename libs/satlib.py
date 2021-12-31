import urllib.request

TLE_FILE = "config/tles.txt"


def get_tles(sat_name):
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
    with open(TLE_FILE, "w") as f:
        f.write(urllib.request.urlopen(sat_url).read().decode())


def get_doppler_shift(frequency, velocity):
    c = 299792458.0  # m/s

    # return velocity / 299792458.0 * frequency
    return int(c / (c + velocity) * frequency - frequency)


def get_shifted(freq, doppler, side):
    if side == "up":
        return int(freq - doppler)
    elif side == "down":
        return int(freq + doppler)
