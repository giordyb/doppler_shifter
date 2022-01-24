"""
pygame-menu
https://github.com/ppizarror/pygame-menu

EXAMPLE - TIMER CLOCK
Example file, timer clock with in-menu options.
"""


__all__ = ["main"]
import sys
import os
import logging
import subprocess

logger = logging.getLogger(__name__)
DEBUG = bool(os.getenv("DEBUG", False))
sys.path.append("/usr/local/lib/python3.9/site-packages/")

import Hamlib

import pygame
import pygame_menu
from pygame_menu.examples import create_example_window
from libs.satlib import (
    get_satellite,
    update_tles,
    get_observer,
)
from libs.commonlib import (
    configure_rig,
    create_slider,
    recalc_shift_and_pos,
    restart_rig,
    shutdown,
)
from libs.constants import (
    RIG_MODES,
    RIG_VFOS,
    H_SIZE,
    W_SIZE,
    SAT_LIST,
    CONFIG,
    RIG_STATUS,
    WHITE,
    RED,
    GREEN,
    DEFAULT_RIG_UP,
    DEFAULT_RIG_DOWN,
)
from libs.gpslib import poll_gps
from pygame.locals import Color
from pygame_menu.widgets.core.widget import Widget

from random import randrange
from typing import List, Tuple, Optional


CURRENT_SAT_CONFIG = SAT_LIST[0]
update_tles(CONFIG["sat_url"])

surface: Optional["pygame.Surface"] = None

Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

CURRENT_SAT_OBJECT = get_satellite(CURRENT_SAT_CONFIG)

ON_BEACON = False
RIG_UP = configure_rig(Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_UP, CONFIG)
RIG_DOWN = configure_rig(
    Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_DOWN, CONFIG
)
# RIG_DOWN.set_vfo_opt(0)

SAVED_UP_FREQ = 0
SAVED_DOWN_FREQ = 0


LOCKED = True

RUN = False
RANGE_SLIDER_UP = create_slider(CURRENT_SAT_CONFIG, "up")
RANGE_SLIDER_DOWN = create_slider(CURRENT_SAT_CONFIG, "down")


def changefreq(value=0):
    global CURRENT_DOWN_FREQ
    CURRENT_DOWN_FREQ = CURRENT_DOWN_FREQ + value


def change_rig(rigtuple, rigidx, RIG):
    global CONFIG
    rigdata, rigidx = rigtuple
    rigname, _, _ = rigdata
    print(f"rigname: {rigname}, rigidx {rigidx}, {RIG.rig_name}")
    RIG.close()
    RIG = configure_rig(RIG, rigidx, CONFIG)
    RIG.open()
    change_sat(None, CURRENT_SAT_CONFIG)


def set_slider(type="center"):
    if CURRENT_SAT_CONFIG["up_mode"] == "FM":
        RANGE_SLIDER_UP._visible = False
        RANGE_SLIDER_DOWN._visible = False
        # RANGE_SLIDER_UP._range_values = (
        #    CURRENT_SAT_CONFIG["up_start"] - 1,
        #    CURRENT_SAT_CONFIG["up_end"] + 1,
        # )
        # RANGE_SLIDER_DOWN._range_values = (
        #    CURRENT_SAT_CONFIG["down_start"] - 1,
        #    CURRENT_SAT_CONFIG["down_end"] + 1,
        # )
    else:
        RANGE_SLIDER_UP._visible = True
        RANGE_SLIDER_DOWN._visible = True
        RANGE_SLIDER_UP._range_values = (
            CURRENT_SAT_CONFIG["up_start"],
            CURRENT_SAT_CONFIG["up_end"],
        )
        RANGE_SLIDER_DOWN._range_values = (
            CURRENT_SAT_CONFIG["down_start"],
            CURRENT_SAT_CONFIG["down_end"],
        )


def change_sat(title, newsat) -> None:
    global CURRENT_SAT_CONFIG
    global CURRENT_SAT_OBJECT
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    CURRENT_SAT_CONFIG = newsat
    CURRENT_SAT_OBJECT = get_satellite(newsat)
    CURRENT_UP_FREQ = CURRENT_SAT_CONFIG["up_center"]
    CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG["down_center"]
    RIG_UP.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["up_mode"]])

    if CURRENT_SAT_CONFIG["up_mode"] == "FM":
        if "TH-D74" in RIG_DOWN.rig_name:
            RIG_DOWN.set_vfo(RIG_VFOS[RIG_DOWN.vfo_name])
            RIG_DOWN.set_level(Hamlib.RIG_LEVEL_SQL, 0.0)
            RIG_DOWN.set_ts(RIG_VFOS[RIG_DOWN.vfo_name], 5000)
        if CURRENT_SAT_CONFIG["tone"] == "0.0":
            RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)
        else:
            RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)
            RIG_UP.set_ctcss_tone(
                RIG_VFOS[RIG_UP.vfo_name],
                int(CURRENT_SAT_CONFIG["tone"].replace(".", "")),
            )
    else:
        if "TH-D74" in RIG_DOWN.rig_name:
            RIG_DOWN.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["down_mode"]])
            RIG_DOWN.set_ts(RIG_VFOS[RIG_DOWN.vfo_name], 100)
        RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)

    RIG_DOWN.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["down_mode"]])

    set_slider()


def tune_beacon():
    global SAVED_UP_FREQ
    global SAVED_DOWN_FREQ
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    global ON_BEACON
    if ON_BEACON:
        CURRENT_UP_FREQ = SAVED_UP_FREQ
        CURRENT_DOWN_FREQ = SAVED_DOWN_FREQ
        bcnbt._background_color = None
        ON_BEACON = False
        set_slider()
    else:
        SAVED_UP_FREQ = CURRENT_UP_FREQ
        SAVED_DOWN_FREQ = CURRENT_DOWN_FREQ
        CURRENT_UP_FREQ = CURRENT_SAT_CONFIG.get(
            "beacon", CURRENT_SAT_CONFIG["up_center"]
        )
        CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG.get(
            "beacon", CURRENT_SAT_CONFIG["down_center"]
        )
        ON_BEACON = True
        bcnbt._background_color = RED
        set_slider(type="beacon")


def stop_start():
    global RUN
    if RUN == True:
        RUN = False
        runbt._background_color = RED
    else:
        RUN = True
        runbt._background_color = GREEN


def tune_center():
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    CURRENT_UP_FREQ = CURRENT_SAT_CONFIG["up_center"]
    CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG["down_center"]
    set_slider()
    bcnbt._background_color = None


"""
Main program.

:param test: Indicate function is being tested
:return: None
"""

# Create window

surface = create_example_window("Sat", (W_SIZE, H_SIZE), flags=pygame.FULLSCREEN)

common_theme = pygame_menu.themes.THEME_DEFAULT.copy()
common_theme.title_font_size = 30
common_theme.font = pygame_menu.font.FONT_FIRACODE
common_theme.widget_font_size = 25
common_theme.widget_alignment = pygame_menu.locals.ALIGN_LEFT
common_theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_TITLE_ONLY_DIAGONAL

# -------------------------------------------------------------------------
# Create SAT MENU
# -------------------------------------------------------------------------

sat_menu = pygame_menu.Menu(
    height=H_SIZE,
    onclose=pygame_menu.events.RESET,
    title="Sats",
    width=W_SIZE,
    theme=common_theme,
    touchscreen=True,
)

sat_tuples = [(x["display_name"], x) for x in SAT_LIST]
satselector = sat_menu.add.selector(
    title="",
    items=sat_tuples,
    default=0,
    onchange=change_sat,
    style="fancy",
)
satselector.scale(1.4, 1.4)

sat_menu.add.vertical_margin(30)
sat_menu.add.clock(font_size=25, font_name=pygame_menu.font.FONT_DIGITAL)
sat_menu.add.button("Return to Menu", pygame_menu.events.BACK)
sat_menu.add.button("Shutdown", shutdown)
sat_menu.add.button("Quit", pygame.QUIT)

# -------------------------------------------------------------------------
# Create Radio MENU
# -------------------------------------------------------------------------

radio_menu = pygame_menu.Menu(
    height=H_SIZE,
    theme=common_theme,
    title="Radio",
    width=W_SIZE,
    touchscreen=True,  # Fullscreen
)

radio_menu.add.dropselect(
    "Uplink",
    [(x["rig_name"], ind, RIG_UP) for ind, x in enumerate(CONFIG["rigs"])],
    onchange=change_rig,
    selection_box_height=5,
    default=RIG_UP.rig_num,
)

radio_menu.add.button("restart downlink rig", lambda: restart_rig("down"))
radio_menu.add.button("restart uplink rig", lambda: restart_rig("up"))
radio_menu.add.button(
    "start kappanhang",
    lambda: subprocess.run(["systemctl", "--user", "start", "kappanhang"]),
)
radio_menu.add.dropselect(
    "Downlink",
    [(x["rig_name"], ind, RIG_DOWN) for ind, x in enumerate(CONFIG["rigs"])],
    onchange=change_rig,
    selection_box_height=5,
    default=RIG_DOWN.rig_num,
)


radio_menu.add.vertical_margin(25)

radio_menu.add.button("Return to Menu", pygame_menu.events.BACK)

# -------------------------------------------------------------------------
# Create Main menu
# -------------------------------------------------------------------------

main_menu = pygame_menu.Menu(
    enabled=True,
    height=H_SIZE,
    theme=common_theme,
    title="Main Menu",
    width=W_SIZE,
    touchscreen=True,
)
az_el_label = main_menu.add.label(
    title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
)
up_label1 = main_menu.add.label(
    title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
)
up_label2 = main_menu.add.label(
    title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
)
down_label1 = main_menu.add.label(
    title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
)
down_label2 = main_menu.add.label(
    title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
)
sat_bt = main_menu.add.button(
    sat_menu.get_title(),
    sat_menu,
    float=True,
    align=pygame_menu.locals.ALIGN_RIGHT,
)
sat_bt.translate(-0, -150)

radiobt = main_menu.add.button(
    radio_menu.get_title(),
    radio_menu,
    float=True,
    align=pygame_menu.locals.ALIGN_RIGHT,
)

radiobt.translate(-0, -100)
bcnbt = main_menu.add.button(
    "Beacon",
    tune_beacon,
    float=True,
    align=pygame_menu.locals.ALIGN_RIGHT,
)

bcnbt.translate(-0, -60)
centerbt = main_menu.add.button(
    "Center",
    tune_center,
    float=True,
    align=pygame_menu.locals.ALIGN_RIGHT,
)
centerbt.translate(-0, -10)
centerbt.border = 1
centerbt.border_color = (
    255,
    255,
    255,
    255,
)
runbt = main_menu.add.button(
    "On/Off",
    stop_start,
    float=True,
    align=pygame_menu.locals.ALIGN_RIGHT,
)
runbt.translate(-0, 40)
runbt._background_color = RED

sliderup = main_menu.add.generic_widget(RANGE_SLIDER_UP, configure_defaults=True)
sliderup.readonly = True
sliderup._font_readonly_color = WHITE
sliderdown = main_menu.add.generic_widget(RANGE_SLIDER_DOWN, configure_defaults=True)
sliderdown.readonly = True
sliderdown._font_readonly_color = WHITE
change_sat("", CURRENT_SAT_CONFIG)
# -------------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------------
observer = get_observer(CONFIG)
pygame_icon = pygame.image.load("images/300px-DopplerSatScheme.bmp")
pygame.display.set_icon(pygame_icon)

while True:
    if RIG_UP.error_status != 0:
        logger.warning(f"rigup error: {RIG_UP.error_status}")
        RIG_UP = configure_rig(RIG_UP, RIG_UP.rig_num, CONFIG)

    if RIG_DOWN.error_status != 0:
        logger.warning(f"rigdown error: {RIG_DOWN.error_status}")
        RIG_DOWN = configure_rig(RIG_UP, RIG_UP.rig_num, CONFIG)

    if CURRENT_SAT_CONFIG["up_mode"] != "FM":
        sidestring = f"BCN {CURRENT_SAT_CONFIG.get('beacon',CURRENT_SAT_CONFIG['down_center']):,.0f}".replace(
            ",", "."
        )
    else:
        sidestring = f"TONE {CURRENT_SAT_CONFIG.get('tone', None)}"
    main_menu.set_title(f"{CURRENT_SAT_CONFIG['display_name']} - {sidestring}")
    if LOCKED:
        lckstr = "Locked"
        az_el_label.set_background_color(None)
    else:
        lckstr = "UnLocked"
        az_el_label.set_background_color((255, 0, 0))

    if RUN:

        az, ele, shift_down, shift_up, shifted_down, shifted_up = recalc_shift_and_pos(
            observer, CURRENT_SAT_OBJECT, CURRENT_UP_FREQ, CURRENT_DOWN_FREQ
        )
        RIG_UP.set_freq(RIG_VFOS[RIG_UP.vfo_name], shifted_up)
        RIG_DOWN.set_freq(RIG_VFOS[RIG_DOWN.vfo_name], shifted_down)
        rf_level = int(RIG_UP.get_level_f(Hamlib.RIG_LEVEL_RFPOWER) * 100)

        az_el_label.set_title(f"Az {az} El {ele} {lckstr} TXPWR {rf_level}%")
        up_label1.set_title(
            f"UP: {CURRENT_UP_FREQ:,.0f} - {CURRENT_SAT_CONFIG['up_mode']} - {RIG_STATUS[RIG_UP.error_status]}".replace(
                ",", "."
            ),
        )
        up_label2.set_title(
            f"UP: {shifted_up:,.0f} SHIFT: {abs(shift_up)}".replace(",", ".")
        )

        down_label1.set_title(
            f"DN: {CURRENT_DOWN_FREQ:,.0f} - {CURRENT_SAT_CONFIG['down_mode']} - {RIG_STATUS[RIG_DOWN.error_status]}".replace(
                ",", "."
            )
        )

        down_label2.set_title(
            f"DN: {shifted_down:,.0f} SHIFT: {abs(shift_down)}".replace(",", ".")
        )
        if CURRENT_UP_FREQ in range(
            CURRENT_SAT_CONFIG["up_start"], CURRENT_SAT_CONFIG["up_end"]
        ):
            RANGE_SLIDER_UP.set_value(CURRENT_UP_FREQ)

        if CURRENT_DOWN_FREQ in range(
            CURRENT_SAT_CONFIG["down_start"], CURRENT_SAT_CONFIG["down_end"]
        ):

            RANGE_SLIDER_DOWN.set_value(CURRENT_DOWN_FREQ)

        # down_range.set_value(CURRENT_DOWN_FREQ)

        # Application events
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            exit()
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["freq_up"]
        ):
            CURRENT_UP_FREQ += 1 * CONFIG["frequency_step"]
            if LOCKED:
                CURRENT_DOWN_FREQ -= 1 * CONFIG["frequency_step"]
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["freq_down"]
        ):
            CURRENT_UP_FREQ -= 1 * CONFIG["frequency_step"]
            if LOCKED:
                CURRENT_DOWN_FREQ += 1 * CONFIG["frequency_step"]

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["lock_vfo"]
        ):
            LOCKED = not LOCKED
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["tune_center"]
        ):
            tune_center()
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["tune_beacon"]
        ):
            tune_beacon()
        if DEBUG:
            if event.type == pygame.MOUSEBUTTONDOWN:
                print(f"pressed mouse button {event.button}")

    main_menu.update(events)
    main_menu.draw(surface)

    # Flip surface
    pygame.display.flip()


RIG_UP.close()
RIG_DOWN.close()
