from gps3 import gps3
import logging
import math

logger = logging.getLogger(__name__)
import time


def dd2dms(deg):
    f, d = math.modf(deg)
    s, m = math.modf(abs(f) * 60)
    return d + ((m + s) / 100)


"""def poll_gps():
    counter = 0
    gps_socket = agps3.GPSDSocket()
    data_stream = agps3.DataStream()
    try:
        gps_socket.connect()
        gps_socket.watch()
        logger.warning("checking gps")
        for new_data in gps_socket:
            if new_data and counter < 5:
                data_stream.unpack(new_data)
                if not isinstance(data_stream.lat, str):
                    lat = str(dd2dms(data_stream.lat))
                    lon = str(dd2dms(data_stream.lon))
                    alt = str(data_stream.alt)
                    logging.warning(f"Latitude = {lat}")
                    logging.warning(f"Longitude = {lon}")
                    logging.warning(f"Altitude = {alt}")
                    if counter > 5:
                        return lat, lon, alt, True
                counter += 1
                time.sleep(1)
            else:
                logging.warning("no gps")
                return "n/a", "n/a", "n/a", False
    except:
        logging.warning("no gps")
        return "n/a", "n/a", "n/a", False"""


def poll_gps():
    counter = 0
    try:
        gps_socket = gps3.GPSDSocket()
        data_stream = gps3.DataStream()
        gps_socket.connect()
        gps_socket.watch()
        logger.warning("checking gps")

        counter = 0
        for new_data in gps_socket:
            if new_data:
                data_stream.unpack(new_data)
                lat = data_stream.TPV["lat"]
                lon = data_stream.TPV["lon"]
                alt = data_stream.TPV["alt"]
                print(f"lat: {lat}, lon: {lon}, alt: {alt}")
                if lat != "n/a":
                    return str(dd2dms(lat)), str(dd2dms(lon)), alt, True
            elif counter > 300000:
                return "n/a", "n/a", "n/a", False
            counter += 1

    except:
        logging.warning("no gps")
        return "n/a", "n/a", "n/a", False
