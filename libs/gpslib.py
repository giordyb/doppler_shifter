from gps3 import agps3


def poll_gps(rootLogger):
    counter = 0
    gps_socket = agps3.GPSDSocket()
    data_stream = agps3.DataStream()
    try:
        gps_socket.connect()
        gps_socket.watch()

        for new_data in gps_socket:
            if new_data:
                if counter > 10:
                    return data_stream.lat, data_stream.lon, data_stream.alt
                data_stream.unpack(new_data)
                rootLogger.warning(f"Altitude = {data_stream.alt}")
                rootLogger.warning(f"Latitude = {data_stream.lat}")
                rootLogger.warning(f"Longitude = { data_stream.lon}")

                counter += 1
    except:
        rootLogger.warning("no gps")
        return "n/a", "n/a", "n/a"
