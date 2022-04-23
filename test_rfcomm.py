#! /usr/bin/python
import serial

bluetoothSerial = serial.Serial( "/dev/rfcomm0", baudrate=112500 )

while 1:
        bluetoothSerial.writelines("AZ EL .".encode())
        x=bluetoothSerial.readline()
        print(x)