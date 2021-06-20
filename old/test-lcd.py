#%%
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


lcd = init_lcd()

# %%
lcd.clear()
lcd.write_string("\x38")

up_arrow = (0b00100, 0b01110, 0b11111, 0b00000, 0b00100, 0b01110, 0b11111, 0b00000)
down_arrow = (0b11111, 0b01110, 0b00100, 0b00000, 0b11111, 0b01110, 0b00100, 0b00000)
lcd.create_char(0, up_arrow)
lcd.write_string("\x00")
lcd.create_char(1, down_arrow)
lcd.write_string("\x01")
# %%
