import urllib.request


def get_tles(sat_name):

    with open("config/nasabare.txt", "r") as f:
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
    with open("config/nasabare.txt", "w") as f:
        f.write(urllib.request.urlopen(sat_url).read().decode())
    XW3_TLES = """
    XW-3
    1 99999U 21360.14997609  .00000032  00000-0  10363-4 0 00007
    2 99999 098.5836 072.3686 0004232 307.2415 261.3002 14.38559758000156
    """
    file1 = open("config/nasabare.txt", "a")  # append mode
    file1.write(XW3_TLES)
    file1.close()


def get_doppler_shift(frequency, velocity):
    c = 299792458.0  # m/s

    # return velocity / 299792458.0 * frequency
    return int(c / (c + velocity) * frequency - frequency)


def get_shifted(freq, doppler, side):
    if side == "up":
        return int(freq - doppler)
    elif side == "down":
        return int(freq + doppler)
