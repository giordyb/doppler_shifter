#%%
#!/usr/bin/python
import csv
import os
import platform
import sys
import time

import serial

SERIAL = "/dev/cu.usbmodem14201"

ser = serial.Serial(
    SERIAL,
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.5,
)
SERIAL = SERIAL
ser.flushInput()
ser.flushOutput()

ser.write(f"ID\r".encode())
print(ser.read(50).decode())


#%%
