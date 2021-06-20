#%%
import sys
import time
from RPLCD import i2c

sys.path.append("/usr/local/lib/python3.7/site-packages")
import Hamlib


lcdmode = "i2c"
cols = 20
rows = 4
charmap = "A00"
i2c_expander = "PCF8574"
address = 0x27
port = 1
lcd = i2c.CharLCD(
    i2c_expander, address, port=port, charmap=charmap, cols=cols, rows=rows
)
Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_TRACE)

my_rig = Hamlib.Rig(Hamlib.RIG_MODEL_THD74)

my_rig.set_conf("rig_pathname", "/dev/ttyACM0")
my_rig.set_conf("retry", "5")


# %%
my_rig.open()
VFO_B = 2
# my_rig.set_vfo(1)
my_rig.set_vfo(VFO_B)
lcd.clear()
while True:

    (mode, width) = my_rig.get_mode(VFO_B)
    modestr = Hamlib.rig_strrmode(mode)
    bwstr = str(width)
    freq = "{0:,}".format(my_rig.get_freq(VFO_B))
    lcd.cursor_pos = (0, 0)
    lcd.write_string(f"Mode: {modestr} BW: {bwstr}")
    lcd.write_string(f"Batt: 80")
    lcd.crlf()
    lcd.crlf()
    my_rig.get_level()
    lcd.write_string(f"{freq} Mhz")

my_rig.set_freq(2, 145275000)
# time.sleep(1)
print(Hamlib.rigerror(my_rig.error_status))
# %%

my_rig.get_mem()
# %%
(mode, width) = my_rig.get_mode()
print("mode:\t\t\t%s\nbandwidth:\t\t%s" % (Hamlib.rig_strrmode(mode), width))
my_rig.set_mode(Hamlib.RIG_MODE_FM)
my_rig.set_split_mode(1, 1)
# %%
while True:
    print(my_rig.get_freq(2))
# %%
my_rig.open()
VFO_A, VFO_B = 1, 2
# my_rig.set_vfo(1)
my_rig.set_vfo(VFO_A)

my_rig.set_vfo(VFO_B)
my_rig.set_freq(VFO_B, 145235000)
print(my_rig.get_level_i(Hamlib.RIG_LEVEL_STRENGTH))

print(Hamlib.rigerror(my_rig.error_status))

# %%
