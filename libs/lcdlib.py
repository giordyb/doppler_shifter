from RPLCD import i2c
import logging

logger = logging.getLogger(__name__)


class Fake_LCD:
    def write_string(self, string):
        logger.warning(f"fakelcd: {string}")

    def crlf(self):
        logger.warning("fakelcd CLCR")

    def clear(self):
        pass

    def home(self):
        pass


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
):

    lcd.home()
    upchar = "\x00"
    # 1st line - don't use log_msg because it's too slow
    if current_up not in sat_up_range:
        upchar = "X"
    msg_str = f"{upchar} {int(current_up):,.0f}".replace(",", ".")
    msg_str += f" +{str(abs(shift_up)).zfill(5)}"

    lcd.write_string(msg_str.ljust(20, " "))
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
        f"{firstchar} {int(current_down):,.0f} -{str(abs(shift_down)).zfill(5)}".replace(
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
        )
    except:
        return Fake_LCD()

    return lcd
