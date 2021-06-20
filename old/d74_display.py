#!/usr/bin/python
import csv
import os
import platform
import sys
import time

import serial


class D74:
    ser = None
    a_b = None
    SERIAL = None

    def __init__(self, SERIAL):
        self.ser = serial.Serial(
            SERIAL,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0.5,
        )
        self.SERIAL = SERIAL
        self.ser.flushInput()
        self.ser.flushOutput()

    # def get_mode(self, vfo):
    #    self.ser.write(
    #        f"MD {vfo}\r".encode()
    #    )  # sets selected band (0 = band a, 1 = band b)
    #    mode_data = self.ser.read(4).decode()
    #    self.ser.flushInput()
    #    self.ser.flushOutput()
    #    return mode_data
    def get_squelch(self):
        self.get_active_vfo()

        self.ser.write(
            f"BY {self.a_b}\r".encode()
        )  # sets selected band (0 = band a, 1 = band b)
        mode_data = self.ser.read(4).decode()
        self.ser.flushInput()
        self.ser.flushOutput()
        if int(mode_data.split()[1]) == 0:
            return "C"
        if int(mode_data.split()[1]) == 1:
            return "O"

    def get_active_vfo(self):
        self.ser.write("BC\r".encode())  # sets selected band (0 = band a, 1 = band b)
        bnd_data = self.ser.read(4).decode()
        self.a_b = bnd_data[3]
        self.ser.flushInput()
        self.ser.flushOutput()

    def get_battery(self):
        self.ser.write(
            "BL\r".encode()
        )  # get battery capacity to confirm proper operation
        init_data = self.ser.read(4).decode()
        if init_data[3] == "0":
            p_f = "<25%"
        elif init_data[3] == "1":
            p_f = ">25%"
        elif init_data[3] == "2":
            p_f = ">50%"
        elif init_data[3] == "3":
            p_f = ">75%"
        elif init_data[3] == "4":
            p_f = "Charging"
        else:
            p_f = "error"
            self.__init__(self.SERIAL)
        # else:
        #    raise Exception("TH-D74 FAIL")
        self.ser.flushInput()
        self.ser.flushOutput()
        return p_f

    def get_freq(self):
        self.get_active_vfo()
        freq_active = f"FO {self.a_b}\r"
        self.ser.write(freq_active.encode())  # get current frequency and mode
        f_data = self.ser.read(50).decode()
        f_array = f_data.split()[1].split(",")
        freq_string = f"{float(f_array[1]):,.2f}"
        step_size = self.switch_step(f_array[3])
        mode_raw = f_data[31]

        modestr = self.switch_mode(int(mode_raw))
        self.ser.flushInput()
        return freq_string, modestr, step_size

    def switch_mode(self, argument):
        switcher = {
            0: "FM",
            1: "DV",
            2: "AM",
            3: "LSB",
            4: "USB",
            5: "CW",
            6: "NFM",
            7: "DR",
            8: "WFM",
            9: "R-CW",
        }
        return switcher.get(argument, "INV")

    def switch_step(self, argument):
        switcher = {
            "0": 5,
            "1": 6.25,
            "2": 8.33,
            "3": 9,
            "4": 10,
            "5": 12.5,
            "6": 15,
            "7": 20,
            "8": 25,
            "9": 30,
            "A": 50,
            "B": 100,
        }
        return switcher.get(argument, "INV")


def init_lcd():
    from RPLCD import i2c

    lcdmode = "i2c"
    cols = 20
    rows = 4
    charmap = "A00"
    i2c_expander = "PCF8574"
    address = 0x27
    port = 1
    return i2c.CharLCD(
        i2c_expander, address, port=port, charmap=charmap, cols=cols, rows=rows
    )


class fakelcd:
    screen = None
    myfont = None
    row = 0

    def __init__(self, chars, lines):
        pygame.init()
        size = [12 * chars, 20 * lines]
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Mock LCD")
        self.myfont = pygame.font.SysFont("monospace", 20)

    def write_string(self, mystr):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        line = self.myfont.render(mystr, 2, (255, 255, 0))
        self.screen.blit(line, (0, 20 * self.row))
        pygame.display.flip()

    def crlf(self):
        self.row = self.row + 1

    def clear(self):
        self.row = 0
        black = 0, 0, 0
        self.screen.fill(black)


if platform.system() == "Linux":
    lcd = init_lcd()
    SERIAL = "/dev/ttyACM0"
else:
    import pygame

    SERIAL = "/dev/cu.usbmodem141101"
    lcd = fakelcd(20, 4)

# Functions definition


# Try to connect to the D74 and run the program

my_d74 = D74(SERIAL)
lcd.clear()

while 1:

    freq_string, mode, step = my_d74.get_freq()
    freq_out = f"{freq_string} {mode}"
    lcd.write_string(f"Step {step}Khz SQ {my_d74.get_squelch()}".ljust(20, " "))
    lcd.crlf()
    lcd.write_string(freq_out)
    lcd.crlf()
    lcd.write_string("")
    lcd.crlf()

    lcd.write_string(f"Batt: {my_d74.get_battery()}")
    # time.sleep(3)  # polls the D74 ten times per second for changes
    lcd.cursor_pos = (0, 0)
    # print(lcd_out)
# if an error is encountered at any point,
#  print a message to the LCD and shutdown the Pi


#%%
