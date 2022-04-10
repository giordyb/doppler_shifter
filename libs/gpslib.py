from gps3 import agps3
import logging
import math

logger = logging.getLogger(__name__)
import time


def dd2dms(deg):
    f, d = math.modf(deg)
    s, m = math.modf(abs(f) * 60)
    return (d, m, s * 60)


def poll_gps():
    counter = 0
    gps_socket = agps3.GPSDSocket()
    data_stream = agps3.DataStream()
    try:
        gps_socket.connect()
        gps_socket.watch()
        logger.warning("checking gps")
        for new_data in gps_socket:
            if new_data:
                if counter > 5:
                    gps_socket.close()
                    return data_stream.lat, data_stream.lon, data_stream.alt, True
                data_stream.unpack(new_data)
                logging.warning(f"Latitude = {data_stream.lat}")
                logging.warning(f"Longitude = { data_stream.lon}")
                logging.warning(f"Altitude = {data_stream.alt}")
                counter += 1
                time.sleep(1)
            else:
                logging.warning("no gps")
                return "n/a", "n/a", "n/a", False
    except:
        logging.warning("no gps")
        return "n/a", "n/a", "n/a", False
