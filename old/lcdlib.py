from RPLCD import i2c
import logging

logger = logging.getLogger(__name__)


def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class Fake_LCD:
    def write_string(self, string):
        logger.warning(f"fakelcd: {string}")

    def crlf(self):
        logger.warning("fakelcd CLCR")

    def clear(self):
        pass

    def home(self):
        pass


def get_linear_range_string(current_freq, SELECTED_SAT, side):
    if SELECTED_SAT["up_mode"] != "FM":
        max = 12
        remapped_current_freq = remap(
            current_freq,
            SELECTED_SAT[f"{side}_start"],
            SELECTED_SAT[f"{side}_end"],
            0,
            max,
        )
        remapped_int = int(remapped_current_freq)
        decimals = int(remapped_current_freq % 1 * 100)
        remapped_decimals = round(remap(decimals, 0, 100, 0, 4))
        # print(f"int {remapped_int}")
        # if side == "up":
        #    print(f"int {remapped_int} dec {remapped_decimals} {remapped_current_freq}")
        charlist = [
            "\x03",
            "\x04",
            "\x05",
            "\x06",
            "\x07",
        ]
        if remapped_int in range(0, max + 1):
            string_range = list("_____________")
            string_range[int(remapped_int)] = charlist[remapped_decimals]
            string_range = "".join(string_range)
            return string_range
        else:
            if remapped_current_freq > max:
                return "<<<<<<<<<<<<<"
            else:
                return ">>>>>>>>>>>>>"
    else:
        return "_____FM______"


def write_lcd_loop(
    lcd,
    current_up,
    current_down,
    shifted_up,
    shifted_down,
    shift_up,
    shift_down,
    SELECTED_SAT,
    sat_up_range,
    sat_down_range,
    sat_alt,
    sat_az,
    tune_lock,
    diff,
    rf_level,
):
    rf_power_char = None

    if rf_level == 100:
        rf_power_char = "FL"
    else:
        rf_power_char = rf_level

    lcd.home()
    upchar = "\x00"
    # 1st line - don't use log_msg because it's too slow
    if current_up not in sat_up_range:
        upchar = "X"

    msg_str = f"{upchar}{get_linear_range_string(current_up,SELECTED_SAT,'up')}"
    msg_str += f"-{str(abs(round(shift_up/1000,1))).zfill(3)}"
    msg_str += f"{rf_power_char}"

    lcd.write_string(msg_str)  # .ljust(20, " "))
    lcd.crlf()
    # 2nd line
    if not tune_lock:
        upchar = "\x02"
    lcd.write_string(
        f"{upchar}{SELECTED_SAT['up_mode'][0]}{int(shifted_up):,.0f} D{diff}".ljust(
            20, " "
        ).replace(",", ".")
    )
    lcd.crlf()
    # 3rd line
    if current_down == SELECTED_SAT.get("beacon", None):
        firstchar = "BC"
    elif current_down not in sat_down_range:
        firstchar = "X"
    else:
        firstchar = "\x01"
    lcd.write_string(
        f"{firstchar}{get_linear_range_string(current_down,SELECTED_SAT,'down')}+{str(abs(round(shift_down/1000,1))).zfill(3)}".replace(
            ",", "."
        )
    )
    lcd.crlf()
    # 4th line
    lcd.write_string(
        f"{firstchar}{SELECTED_SAT['down_mode'][0]}{int(shifted_down):,.0f}{sat_alt.zfill(2)}/{sat_az}".ljust(
            20, " "
        ).replace(
            ",", "."
        )
    )


def init_lcd():
    lcdmode = "i2c"
    cols = 20
    rows = 4
    charmap = "A00"
    i2c_expander = "PCF8574"
    address = 0x27
    port = 1
    try:
        lcd = i2c.CharLCD(
            i2c_expander, address, port=port, charmap=charmap, cols=cols, rows=rows
        )
        lcd.create_char(
            0, (0b00100, 0b01110, 0b11111, 0b00000, 0b00100, 0b01110, 0b11111, 0b00000)
        )  # UP ARROW CHAR
        lcd.create_char(
            1, (0b11111, 0b01110, 0b00100, 0b00000, 0b11111, 0b01110, 0b00100, 0b00000)
        )  # DOWN ARROW CHAR

        lcd.create_char(
            2, (0b01110, 0b11011, 0b10000, 0b11111, 0b11111, 0b11011, 0b11011, 0b01110)
        )  # LOCK CHAR

        # inter-char-lines
        lcd.create_char(
            3, (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000)
        )
        lcd.create_char(
            4, (0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000)
        )
        lcd.create_char(
            5, (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100)
        )
        lcd.create_char(
            6, (0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010)
        )
        lcd.create_char(
            7, (0b00001, 0b00001, 0b00001, 0b00001, 0b00001, 0b00001, 0b00001, 0b00001)
        )

    except:
        return Fake_LCD()

    return lcd
