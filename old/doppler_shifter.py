__all__ = ["main"]
import sys
import os
import logging
import subprocess
import argparse
import json
from queue import Queue
from threading import Thread
import os

logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
sys.path.append("/usr/local/lib/python3.9/site-packages/")
os.putenv("SDL_FBDEV", "/dev/fb1")
os.putenv("SDL_MOUSEDRV", "TSLIB")
os.putenv("SDL_MOUSEDEV", "/dev/input/touchscreen")

import Hamlib

import pygame
import pygame_menu
from pygame_menu.examples import create_example_window
from libs.satlib import get_satellite, save_conf, update_tles, get_observer, load_conf
from libs.commonlib import (
    configure_rig,
    configure_rot,
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
    RIG_STATUS,
    WHITE,
    RED,
    GREEN,
    DEFAULT_RIG_UP,
    DEFAULT_RIG_DOWN,
)
from pygame.locals import Color
from pygame_menu.widgets.core.widget import Widget

from random import randrange
from typing import List, Tuple, Optional

all_args = argparse.ArgumentParser()
all_args.add_argument(
    "-c",
    "--configpath",
    required=False,
    help="config file path",
    default="config/config.json",
)
args = vars(all_args.parse_args())

CONFIG = load_conf(args["configpath"])


CURRENT_SAT_CONFIG = SAT_LIST[CONFIG.get("loaded_sat", 0)]
update_tles(CONFIG["sat_url"])

surface: Optional["pygame.Surface"] = None

Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

CURRENT_SAT_OBJECT = get_satellite(CURRENT_SAT_CONFIG)
CURRENT_UP_FREQ = 0
CURRENT_DOWN_FREQ = 0
ON_BEACON = False
RIG_UP = configure_rig(Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_UP, CONFIG)
RIG_DOWN = configure_rig(
    Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_DOWN, CONFIG
)
# RIG_DOWN.set_vfo_opt(0)

ROT = configure_rot(Hamlib.Rot(Hamlib.ROT_MODEL_NETROTCTL), CONFIG)
SAVED_UP_FREQ = 0
SAVED_DOWN_FREQ = 0
DIFF_FREQ = 0

LOCKED = True

RUN = False
ROTATOR = False
RANGE_SLIDER_UP = create_slider(CURRENT_SAT_CONFIG, "up")
RANGE_SLIDER_DOWN = create_slider(CURRENT_SAT_CONFIG, "down")


def changefreq(value=0):
    global CURRENT_DOWN_FREQ
    CURRENT_DOWN_FREQ = CURRENT_DOWN_FREQ + value


def change_rig_up(rigtuple, rigidx, RIG):
    global CONFIG
    global RIG_UP
    rigdata, rigidx = rigtuple
    rigname, _, _ = rigdata
    print(f"rigname: {rigname}, rigidx {rigidx}, {RIG.rig_name}")
    RIG.close()
    RIG = configure_rig(RIG_UP, rigidx, CONFIG)
    RIG.open()
    change_sat(None, CURRENT_SAT_CONFIG)
    RIG_UP = RIG


def change_rig_down(rigtuple, rigidx, RIG):
    global CONFIG
    global RIG_DOWN
    rigdata, rigidx = rigtuple
    rigname, _, _ = rigdata
    print(f"rigname: {rigname}, rigidx {rigidx}, {RIG.rig_name}")
    RIG.close()
    RIG = configure_rig(RIG_DOWN, rigidx, CONFIG)
    RIG.open()
    change_sat(None, CURRENT_SAT_CONFIG)
    RIG_DOWN = RIG


def set_slider(type="center"):
    if CURRENT_SAT_CONFIG["up_mode"] == "FM":
        RANGE_SLIDER_UP._visible = True
        RANGE_SLIDER_DOWN._visible = True
        RANGE_SLIDER_UP._range_values = (0, 1)
        #    CURRENT_SAT_CONFIG["up_start"] - 1,
        #    CURRENT_SAT_CONFIG["up_end"] + 1,
        # )
        RANGE_SLIDER_DOWN._range_values = (0, 1)
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


def change_sat(satargs, newsat):
    global CURRENT_SAT_CONFIG
    global CURRENT_SAT_OBJECT
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    global DIFF_FREQ
    global CONFIG
    global args
    satinfo, satindex = satargs
    CURRENT_SAT_CONFIG = newsat
    CURRENT_SAT_CONFIG["index"] = satindex
    CURRENT_SAT_OBJECT = get_satellite(newsat)
    CURRENT_UP_FREQ = CURRENT_SAT_CONFIG["up_center"]
    CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG["down_center"]
    DIFF_FREQ = CURRENT_SAT_CONFIG.get("saved_diff_freq", 0)
    RIG_UP.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["up_mode"]])
    RIG_UP.set_vfo(RIG_VFOS[RIG_UP.vfo_name])
    RIG_DOWN.set_vfo(RIG_VFOS[RIG_DOWN.vfo_name])

    if CURRENT_SAT_CONFIG["up_mode"] == "FM":
        if CURRENT_SAT_CONFIG["tone"] == "0.0":
            RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)
            RIG_UP.tone = False
        else:
            RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)
            RIG_UP.set_ctcss_tone(
                RIG_VFOS[RIG_UP.vfo_name],
                int(CURRENT_SAT_CONFIG["tone"].replace(".", "")),
            )
            RIG_UP.tone = int(CURRENT_SAT_CONFIG["tone"].replace(".", ""))
    else:
        RIG_DOWN.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["down_mode"]])
        RIG_DOWN.set_ts(RIG_VFOS[RIG_DOWN.vfo_name], 100)
        RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)
        RIG_UP.tone = False

    RIG_DOWN.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["down_mode"]])

    set_slider()
    CONFIG["loaded_sat"] = CURRENT_SAT_CONFIG["index"]
    save_conf(args["configpath"], CONFIG)


def tune_beacon():
    global DIFF_FREQ
    global SAVED_DOWN_FREQ
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    global ON_BEACON
    if ON_BEACON:
        # CURRENT_UP_FREQ = SAVED_UP_FREQ
        CURRENT_DOWN_FREQ = SAVED_DOWN_FREQ
        bcnbt._background_color = None
        ON_BEACON = False
        set_slider()
    else:
        # SAVED_UP_FREQ = CURRENT_UP_FREQ
        SAVED_DOWN_FREQ = CURRENT_DOWN_FREQ
        # CURRENT_UP_FREQ = CURRENT_SAT_CONFIG.get(
        #    "beacon", CURRENT_SAT_CONFIG["up_center"]
        # )
        CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG.get(
            "beacon", CURRENT_SAT_CONFIG["down_center"]
        )
        ON_BEACON = True
        bcnbt._background_color = RED
        set_slider(type="beacon")


def start_stop(runbt):
    global RUN
    global RIG_UP
    global RIG_DOWN
    if RUN:
        RUN = False
        runbt._background_color = RED
    else:
        RUN = True
        RIG_UP = configure_rig(RIG_UP, RIG_UP.rig_num, CONFIG)
        RIG_DOWN = configure_rig(RIG_DOWN, RIG_DOWN.rig_num, CONFIG)
        runbt._background_color = GREEN
        RIG_UP.open()
        RIG_DOWN.open()


def enable_rotator():
    global ROTATOR
    if ROTATOR:
        ROTATOR = False
        ROT.set_position(0, 0)
        ROT.close()
        enablerot._background_color = None
    else:
        ROTATOR = True
        ROT.open()
        enablerot._background_color = GREEN


def tune_center():
    global CURRENT_UP_FREQ
    global CURRENT_DOWN_FREQ
    global RANGE_SLIDER_UP
    global RANGE_SLIDER_DOWN
    CURRENT_UP_FREQ = CURRENT_SAT_CONFIG["up_center"]
    CURRENT_DOWN_FREQ = CURRENT_SAT_CONFIG["down_center"] + DIFF_FREQ
    set_slider()
    bcnbt._background_color = None


def swap_rig():
    global RIG_DOWN
    global RIG_UP
    global q_up
    global q_down
    RIG_TEMP = RIG_DOWN
    q_temp = q_down
    RIG_DOWN = RIG_UP
    q_down = q_up
    RIG_UP = RIG_TEMP
    q_up = q_temp
    RIG_UP.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["up_mode"]])
    RIG_DOWN.set_mode(RIG_MODES[CURRENT_SAT_CONFIG["down_mode"]])
    if RIG_UP.tone:
        RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)
        RIG_UP.set_ctcss_tone(
            RIG_VFOS[RIG_UP.vfo_name],
            RIG_UP.tone,
        )
    else:
        RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)


def save_satlist():
    global DIFF_FREQ
    SAT_LIST[CURRENT_SAT_CONFIG["index"]]["saved_diff_freq"] = DIFF_FREQ
    with open("config/satlist.json", "w") as f:
        json.dump(SAT_LIST, f, indent=4)


def change_freq(q, rig):
    global RIG_VFOS
    while True:
        if rig.error_status != 0:
            rig.open()
            logger.warning(f"rig {rig.rig_name}: {rig.error_status}")

        freq = q.get()
        rig.set_freq(RIG_VFOS[rig.vfo_name], freq)
        q.task_done()


def update_rotator(q, rot):
    while True:
        position = q.get()
        rot_azi, rot_ele = position
        rot.set_position(rot_azi, rot_ele)
        q.task_done()


def lock_unlock_vfos():
    global LOCKED
    LOCKED = not LOCKED
    if LOCKED:
        lock_bt._background_color = None
        save_satlist()
    else:
        lock_bt._background_color = RED


"""
Main program.

:param test: Indicate function is being tested
:return: None
"""
q_up = Queue(maxsize=0)
q_down = Queue(maxsize=0)
q_rot = Queue(maxsize=0)

rig_up_thread = Thread(target=change_freq, args=(q_up, RIG_UP))
rig_up_thread.setDaemon(True)
rig_up_thread.start()
rig_down_thread = Thread(target=change_freq, args=(q_down, RIG_DOWN))
rig_down_thread.setDaemon(True)
rig_down_thread.start()
rotator_thread = Thread(target=update_rotator, args=(q_rot, ROT))
rotator_thread.setDaemon(True)
rotator_thread.start()

# Create window

surface = create_example_window("Sat", (W_SIZE, H_SIZE), flags=pygame.FULLSCREEN)

common_theme = pygame_menu.themes.THEME_DEFAULT.copy()
common_theme.title_font_size = 26
common_theme.font = pygame_menu.font.FONT_FIRACODE
common_theme.widget_font_size = 24
common_theme.widget_alignment = pygame_menu.locals.ALIGN_LEFT
common_theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_TITLE_ONLY_DIAGONAL
# common_theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_TITLE_ONLY
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
    touchscreen=True,
)

radio_menu.add.dropselect(
    "Uplink",
    [(x["rig_name"], ind, RIG_UP) for ind, x in enumerate(CONFIG["rigs"])],
    onchange=change_rig_up,
    selection_box_height=5,
    default=RIG_UP.rig_num,
)

radio_menu.add.button("restart downlink rig", lambda: restart_rig("down"))
radio_menu.add.button("restart uplink rig", lambda: restart_rig("up"))
radio_menu.add.button(
    "restart rotator",
    lambda: subprocess.run(["sudo", "systemctl", "restart", "rotator"]),
)
radio_menu.add.dropselect(
    "Downlink",
    [(x["rig_name"], ind, RIG_DOWN) for ind, x in enumerate(CONFIG["rigs"])],
    onchange=change_rig_down,
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
    columns=2,
    rows=7,
    touchscreen=True,
)
lock_bt = main_menu.add.button(
    "test",
    lock_unlock_vfos,
    align=pygame_menu.locals.ALIGN_LEFT,
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
sliderup = main_menu.add.generic_widget(RANGE_SLIDER_UP, configure_defaults=True)
sliderup.readonly = True
sliderup._font_readonly_color = WHITE
sliderdown = main_menu.add.generic_widget(RANGE_SLIDER_DOWN, configure_defaults=True)
sliderdown.readonly = True
sliderdown._font_readonly_color = WHITE

sat_bt = main_menu.add.button(
    sat_menu.get_title(),
    sat_menu,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)

radiobt = main_menu.add.button(
    radio_menu.get_title(),
    radio_menu,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)
bcnbt = main_menu.add.button(
    "Beacon",
    tune_beacon,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)
centerbt = main_menu.add.button(
    "Center",
    tune_center,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)

enablerot = main_menu.add.button(
    "Track",
    enable_rotator,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)
runbt = main_menu.add.button(
    "On/Off",
    lambda: start_stop(runbt),
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)
runbt._background_color = RED
swapbt = main_menu.add.button(
    "swap",
    swap_rig,
    align=pygame_menu.locals.ALIGN_LEFT,
    font_size=23,
)

change_sat(("", CONFIG.get("loaded_sat", 0)), CURRENT_SAT_CONFIG)
# -------------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------------
observer = get_observer(CONFIG)
pygame_icon = pygame.image.load("images/300px-DopplerSatScheme.bmp")
pygame.display.set_icon(pygame_icon)
radio_delay = pygame.time.get_ticks()
radio_status_delay = pygame.time.get_ticks()
rotator_delay = pygame.time.get_ticks()
az_rangelist1 = CONFIG["observer_conf"]["range1"].split("-")
az_rangelist2 = CONFIG["observer_conf"]["range2"].split("-")
curr_rot_azi, curr_rot_ele = 0, 0
rigupstatus = "??"
rigdownstatus = "??"
while True:

    if CURRENT_SAT_CONFIG["up_mode"] != "FM":
        sidestring = f"BCN {CURRENT_SAT_CONFIG.get('beacon',CURRENT_SAT_CONFIG['down_center']):,.0f}".replace(
            ",", "."
        )
    else:
        sidestring = f"TONE {CURRENT_SAT_CONFIG.get('tone', None)}"
    main_menu.set_title(f"{CURRENT_SAT_CONFIG['display_name']} - {sidestring}")

    az, ele, shift_down, shift_up, shifted_down, shifted_up = recalc_shift_and_pos(
        observer, CURRENT_SAT_OBJECT, CURRENT_UP_FREQ, CURRENT_DOWN_FREQ
    )

    if ROTATOR:
        if pygame.time.get_ticks() - rotator_delay > 1000:
            rot_azi = float(az)
            rot_ele = 0.0
            if float(ele) > -4 and (
                rot_azi in range(int(az_rangelist1[0]), int(az_rangelist1[1]))
                or rot_azi in range(int(az_rangelist2[0]), int(az_rangelist2[1]))
            ):
                if float(ele) >= 0:
                    rot_ele = float(ele)
            curr_rot_azi, curr_rot_ele = ROT.get_position()
            logger.warning(f"tracking az {rot_azi} ele {rot_ele}")
            # ROT.set_position(rot_azi, rot_ele)
            rotator_delay = pygame.time.get_ticks()
            if ROT.error_status != 0:
                ROT.open()
                curr_rot_azi, curr_rot_ele = 99, 99

            q_rot.put((rot_azi, rot_ele))

        lock_bt.set_title(
            f"Az {az}/{int(curr_rot_azi)} El {ele}/{int(curr_rot_ele)} {DIFF_FREQ}"
        )  # TXPWR {rf_level}%"

    else:
        lock_bt.set_title(f"Az {az} El {ele} {DIFF_FREQ}")  # TX {rf_level}%")
    if RUN:
        q_down.put(shifted_down)
        """if RIG_UP.error_status != 0:
            logger.warning(f"rigup error: {RIG_UP.error_status}")
            # RIG_UP = configure_rig(RIG_UP, RIG_UP.rig_num, CONFIG)

        if RIG_DOWN.error_status != 0:
            logger.warning(f"rigdown error: {RIG_DOWN.error_status}")
            # RIG_DOWN = configure_rig(RIG_DOWN, RIG_DOWN.rig_num, CONFIG)
        """
        if pygame.time.get_ticks() - radio_status_delay > 1500:
            rigupstatus = RIG_STATUS[RIG_UP.error_status]
            rigdownstatus = RIG_STATUS[RIG_DOWN.error_status]
            radio_status_delay = pygame.time.get_ticks()
        if pygame.time.get_ticks() - radio_delay > 1500:
            q_up.put(shifted_up)
            radio_delay = pygame.time.get_ticks()

    up_label1.set_title(
        f"UP: {CURRENT_UP_FREQ:,.0f} - {CURRENT_SAT_CONFIG['up_mode']} - {RIG_UP.rig_name}:{rigupstatus}".replace(
            ",", "."
        ),
    )
    up_label2.set_title(
        f"UP: {shifted_up:,.0f} SHIFT: {abs(shift_up)}".replace(",", ".")
    )

    down_label1.set_title(
        f"DN: {CURRENT_DOWN_FREQ:,.0f} - {CURRENT_SAT_CONFIG['down_mode']} - {RIG_DOWN.rig_name}:{rigdownstatus}".replace(
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

        # Application events
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.MOUSEWHEEL and event.y < 0:
            CURRENT_DOWN_FREQ -= 1 * CONFIG["frequency_step"]
            if LOCKED:
                CURRENT_UP_FREQ += 1 * CONFIG["frequency_step"]
            else:
                DIFF_FREQ -= 1 * CONFIG["frequency_step"]

        elif event.type == pygame.MOUSEWHEEL and event.y > 0:
            CURRENT_DOWN_FREQ += 1 * CONFIG["frequency_step"]
            if LOCKED:
                CURRENT_UP_FREQ -= 1 * CONFIG["frequency_step"]
            else:
                DIFF_FREQ += 1 * CONFIG["frequency_step"]

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == CONFIG["mouse_buttons"]["lock_vfo"]
        ):
            lock_unlock_vfos()

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
            if event.type == pygame.MOUSEWHEEL:
                #   logger.warning(event)
                # logger.warning(event.x, event.y)
                logger.warning(event.flipped)
            if event.type == pygame.MOUSEBUTTONDOWN:
                print(f"pressed mouse button {event.button}")
            # logger.warning(f"mouse event {event}")

    main_menu.update(events)
    main_menu.draw(surface)

    # Flip surface
    pygame.display.flip()


RIG_UP.close()
RIG_DOWN.close()
