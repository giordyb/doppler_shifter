#%%
import RPi.GPIO as GPIO
from RPLCD import i2c

def init_lcd():

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
def gpio_setup():
    

    GPIO.setmode(GPIO.BCM)

    # set up the GPIO events on those pins
    GPIO.setup(CLK, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(DT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def clicked_prompt(channel):
    global clicked
    clicked = False

# main.py
import sys

if __name__ == "__main__":
    CLK = 17
    DT = 18
    SW = 27
    clicked = True
    gpio_setup()
    GPIO.add_event_detect(SW, GPIO.FALLING, callback=clicked_prompt, bouncetime=150)
    lcd = init_lcd()

    # %%
    lcd.clear()
    lcd.write_string(sys.argv[1])
    while clicked:
        pass
    

