from gps3 import gps3
import logging
import math

logger = logging.getLogger(__name__)
import time


def dd2dms(deg):
    f, d = math.modf(deg)
    s, m = math.modf(abs(f) * 60)
    return d + ((m + s) / 100)


def poll_gps():
    counter = 0
    try:
        gps_socket = gps3.GPSDSocket()
        data_stream = gps3.DataStream()
        gps_socket.connect()
        gps_socket.watch()
        counter = 0
        for new_data in gps_socket:
            if new_data:
                data_stream.unpack(new_data)
                lat = data_stream.TPV["lat"]
                lon = data_stream.TPV["lon"]
                alt = data_stream.TPV["alt"]
                print(f"lat: {lat}, lon: {lon}, alt: {alt}")
                if lat != "n/a":
                    print(counter)
                    return dd2dms(lat), dd2dms(lon), alt, True
            elif counter > 100000:
                print(counter)
                return "n/a", "n/a", "n/a", False
            counter += 1

    except:
        return "n/a", "n/a", "n/a", False


if main
lat, lon, alt = poll_gps()
print(f"final lat: {lat}, lon: {lon}, alt: {alt}")
