from RPLCD import i2c


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
):

    lcd.home()
    if current_up not in sat_up_range:
        lcd.write_string("xx")
    else:
        lcd.write_string("\x00 ")
    lcd.write_string(f"{int(current_up):,.0f} +{str(abs(shift_up)).zfill(5)}")
    lcd.crlf()
    lcd.write_string("\x00 ")
    lcd.write_string(f"{int(shifted_up):,.0f} {SELECTED_SAT['up_mode']}")
    lcd.crlf()
    if current_down == SELECTED_SAT.get("beacon", None):
        lcd.write_string("BC")
    elif current_down not in sat_down_range:
        lcd.write_string("xx")
    else:
        lcd.write_string("\x01 ")
    lcd.write_string(f"{int(current_down):,.0f} -{str(abs(shift_down)).zfill(5)}")
    lcd.crlf()

    lcd.write_string("\x01 ")
    lcd.write_string(f"{int(shifted_down):,.0f} {SELECTED_SAT['down_mode']}")


def init_lcd():
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
    lcd.create_char(
        0, (0b00100, 0b01110, 0b11111, 0b00000, 0b00100, 0b01110, 0b11111, 0b00000)
    )  # UP ARROW CHAR
    lcd.create_char(
        1, (0b11111, 0b01110, 0b00100, 0b00000, 0b11111, 0b01110, 0b00100, 0b00000)
    )  # DOWN ARROW CHAR
    return lcd
