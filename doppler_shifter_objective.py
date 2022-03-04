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
from libs.gpslib import poll_gps
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


class App(object):
    SAVED_UP_FREQ = 0
    CURRENT_UP_FREQ = 0
    CURRENT_DOWN_FREQ = 0
    SAVED_DOWN_FREQ = 0
    DIFF_FREQ = 0
    LOCKED = True
    RUN = False
    ROTATOR = False
    ON_BEACON = False

    def __init__(self, args) -> None:
        self.CONFIG = load_conf(args["configpath"])
        self.CURRENT_SAT_CONFIG = SAT_LIST[self.CONFIG.get("loaded_sat", 0)]
        update_tles(self.CONFIG["sat_url"])
        self.surface: Optional["pygame.Surface"] = None
        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)
        self.CURRENT_SAT_OBJECT = get_satellite(self.CURRENT_SAT_CONFIG)
        self.RIG_UP = configure_rig(
            Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_UP, self.CONFIG
        )
        self.RIG_DOWN = configure_rig(
            Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL), DEFAULT_RIG_DOWN, self.CONFIG
        )
        self.ROT = configure_rot(Hamlib.Rot(Hamlib.ROT_MODEL_NETROTCTL), self.CONFIG)
        self.RANGE_SLIDER_UP = create_slider(self.CURRENT_SAT_CONFIG, "up")
        self.RANGE_SLIDER_DOWN = create_slider(self.CURRENT_SAT_CONFIG, "down")
        self.q_up = Queue(maxsize=0)
        self.q_down = Queue(maxsize=0)
        self.q_rot = Queue(maxsize=0)

        rig_up_thread = Thread(target=self.change_freq, args=(self.q_up, self.RIG_UP))
        rig_up_thread.setDaemon(True)
        rig_up_thread.start()
        rig_down_thread = Thread(
            target=self.change_freq, args=(self.q_down, self.RIG_DOWN)
        )
        rig_down_thread.setDaemon(True)
        rig_down_thread.start()
        rotator_thread = Thread(target=self.update_rotator, args=(self.q_rot, self.ROT))
        rotator_thread.setDaemon(True)
        rotator_thread.start()

        self.surface = create_example_window(
            "Sat", (W_SIZE, H_SIZE), flags=pygame.FULLSCREEN
        )

        common_theme = pygame_menu.themes.THEME_DEFAULT.copy()
        common_theme.title_font_size = 26
        common_theme.font = pygame_menu.font.FONT_FIRACODE
        common_theme.widget_font_size = 23
        common_theme.widget_alignment = pygame_menu.locals.ALIGN_LEFT
        common_theme.title_bar_style = (
            pygame_menu.widgets.MENUBAR_STYLE_TITLE_ONLY_DIAGONAL
        )

        self.sat_menu = pygame_menu.Menu(
            height=H_SIZE,
            onclose=pygame_menu.events.RESET,
            title="Sats",
            width=W_SIZE,
            theme=common_theme,
            touchscreen=True,
        )

        sat_tuples = [(x["display_name"], x) for x in SAT_LIST]
        self.satselector = self.sat_menu.add.selector(
            title="",
            items=sat_tuples,
            default=0,
            onchange=self.change_sat,
            style="fancy",
        )
        self.satselector.scale(1.4, 1.4)

        self.sat_menu.add.vertical_margin(30)
        self.sat_menu.add.clock(font_size=25, font_name=pygame_menu.font.FONT_DIGITAL)
        self.sat_menu.add.button("Return to Menu", pygame_menu.events.BACK)
        self.sat_menu.add.button("Shutdown", shutdown)
        self.sat_menu.add.button("Quit", pygame.QUIT)

        # -------------------------------------------------------------------------
        # Create Radio MENU
        # -------------------------------------------------------------------------

        self.radio_menu = pygame_menu.Menu(
            height=H_SIZE,
            theme=common_theme,
            title="Radio",
            width=W_SIZE,
            touchscreen=True,
        )

        self.radio_menu.add.dropselect(
            "Uplink",
            [
                (x["rig_name"], ind, self.RIG_UP, "up")
                for ind, x in enumerate(self.CONFIG["rigs"])
            ],
            onchange=self.change_rig,
            selection_box_height=5,
            default=self.RIG_UP.rig_num,
        )

        self.radio_menu.add.button("restart downlink rig", lambda: restart_rig("down"))
        self.radio_menu.add.button("restart uplink rig", lambda: restart_rig("up"))
        self.radio_menu.add.button(
            "restart rotator",
            lambda: subprocess.run(["sudo", "systemctl", "restart", "rotator"]),
        )
        self.radio_menu.add.dropselect(
            "Downlink",
            [
                (x["rig_name"], ind, self.RIG_DOWN, "down")
                for ind, x in enumerate(self.CONFIG["rigs"])
            ],
            onchange=self.change_rig,
            selection_box_height=5,
            default=self.RIG_DOWN.rig_num,
        )
        self.radio_menu.add.vertical_margin(25)
        self.radio_menu.add.button("Return to Menu", pygame_menu.events.BACK)

        # -------------------------------------------------------------------------
        # Create Main menu
        # -------------------------------------------------------------------------

        self.main_menu = pygame_menu.Menu(
            enabled=True,
            height=H_SIZE,
            theme=common_theme,
            title="Main Menu",
            width=W_SIZE,
            columns=2,
            rows=7,
            touchscreen=True,
        )
        self.lock_bt = self.main_menu.add.button(
            "test",
            self.lock_unlock_vfos,
            align=pygame_menu.locals.ALIGN_LEFT,
        )

        self.up_label1 = self.main_menu.add.label(
            title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
        )
        self.up_label2 = self.main_menu.add.label(
            title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
        )
        self.down_label1 = self.main_menu.add.label(
            title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
        )
        self.down_label2 = self.main_menu.add.label(
            title="", align=pygame_menu.locals.ALIGN_LEFT, padding=0
        )
        self.sliderup = self.main_menu.add.generic_widget(
            self.RANGE_SLIDER_UP, configure_defaults=True
        )
        self.sliderup.readonly = True
        self.sliderup._font_readonly_color = WHITE
        self.sliderdown = self.main_menu.add.generic_widget(
            self.RANGE_SLIDER_DOWN, configure_defaults=True
        )
        self.sliderdown.readonly = True
        self.sliderdown._font_readonly_color = WHITE

        self.sat_bt = self.main_menu.add.button(
            self.sat_menu.get_title(),
            self.sat_menu,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )

        self.radiobt = self.main_menu.add.button(
            self.radio_menu.get_title(),
            self.radio_menu,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )
        self.bcnbt = self.main_menu.add.button(
            "Beacon",
            self.tune_beacon,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )
        self.centerbt = self.main_menu.add.button(
            "Center",
            self.tune_center,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )

        self.enablerot = self.main_menu.add.button(
            "Track",
            self.enable_rotator,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )
        self.runbt = self.main_menu.add.button(
            "On/Off",
            lambda: self.start_stop(),
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )
        self.runbt._background_color = RED
        self.swapbt = self.main_menu.add.button(
            "swap",
            self.swap_rig,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
        )

        self.change_sat(("", self.CONFIG.get("loaded_sat", 0)), self.CURRENT_SAT_CONFIG)

    # def changefreq(self, value=0):
    #    self.CURRENT_DOWN_FREQ = self.CURRENT_DOWN_FREQ + value

    def change_rig(self, rigtuple, rigidx, RIG, side):
        rigdata, rigidx = rigtuple
        rigname, _, _, _ = rigdata
        config_rig = Hamlib.Rig()
        print(f"rigname: {rigname}, rigidx {rigidx}, {RIG.rig_name}")
        RIG.close()
        if side == "up":
            config_rig = self.RIG_UP
        elif side == "down":
            config_rig = self.RIG_DOWN
        RIG = configure_rig(config_rig, rigidx, self.CONFIG)
        RIG.open()
        self.change_sat(("", self.CONFIG.get("loaded_sat", 0)), self.CURRENT_SAT_CONFIG)
        if side == "up":
            self.RIG_UP = RIG
        elif side == "down":
            self.RIG_DOWN = RIG

    """def change_rig_down(self, rigtuple, rigidx, RIG):
        rigdata, rigidx = rigtuple
        rigname, _, _ = rigdata
        print(f"rigname: {rigname}, rigidx {rigidx}, {RIG.rig_name}")
        RIG.close()
        RIG = configure_rig(self.RIG_DOWN, rigidx, self.CONFIG)
        RIG.open()
        self.change_sat(None, self.CURRENT_SAT_CONFIG)"""

    def set_slider(self, type="center"):
        if self.CURRENT_SAT_CONFIG["up_mode"] == "FM":
            self.RANGE_SLIDER_UP._visible = True
            self.RANGE_SLIDER_DOWN._visible = True
            self.RANGE_SLIDER_UP._range_values = (0, 1)
            self.RANGE_SLIDER_DOWN._range_values = (0, 1)
        else:
            self.RANGE_SLIDER_UP._visible = True
            self.RANGE_SLIDER_DOWN._visible = True
            self.RANGE_SLIDER_UP._range_values = (
                self.CURRENT_SAT_CONFIG["up_start"],
                self.CURRENT_SAT_CONFIG["up_end"],
            )
            self.RANGE_SLIDER_DOWN._range_values = (
                self.CURRENT_SAT_CONFIG["down_start"],
                self.CURRENT_SAT_CONFIG["down_end"],
            )

    def change_sat(self, satargs, newsat):
        global args
        satinfo, satindex = satargs
        self.CURRENT_SAT_CONFIG = newsat
        self.CURRENT_SAT_CONFIG["index"] = satindex
        self.CURRENT_SAT_OBJECT = get_satellite(newsat)
        self.CURRENT_UP_FREQ = self.CURRENT_SAT_CONFIG["up_center"]
        self.CURRENT_DOWN_FREQ = self.CURRENT_SAT_CONFIG["down_center"]
        self.DIFF_FREQ = self.CURRENT_SAT_CONFIG.get("saved_diff_freq", 0)
        self.RIG_UP.set_mode(RIG_MODES[self.CURRENT_SAT_CONFIG["up_mode"]])
        self.RIG_UP.set_vfo(RIG_VFOS[self.RIG_UP.vfo_name])
        self.RIG_DOWN.set_vfo(RIG_VFOS[self.RIG_DOWN.vfo_name])

        if self.CURRENT_SAT_CONFIG["up_mode"] == "FM":
            if self.CURRENT_SAT_CONFIG["tone"] == "0.0":
                self.RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)
                self.RIG_UP.tone = False
            else:
                self.RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)
                self.RIG_UP.set_ctcss_tone(
                    RIG_VFOS[self.RIG_UP.vfo_name],
                    int(self.CURRENT_SAT_CONFIG["tone"].replace(".", "")),
                )
                self.RIG_UP.tone = int(self.CURRENT_SAT_CONFIG["tone"].replace(".", ""))
        else:
            self.RIG_DOWN.set_mode(RIG_MODES[self.CURRENT_SAT_CONFIG["down_mode"]])
            self.RIG_DOWN.set_ts(RIG_VFOS[self.RIG_DOWN.vfo_name], 100)
            self.RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 0)
            self.RIG_UP.tone = False

        self.RIG_DOWN.set_mode(RIG_MODES[self.CURRENT_SAT_CONFIG["down_mode"]])

        self.set_slider()
        self.CONFIG["loaded_sat"] = self.CURRENT_SAT_CONFIG["index"]
        save_conf(args["configpath"], self.CONFIG)

    def tune_beacon(self):
        if self.ON_BEACON:
            # CURRENT_UP_FREQ = SAVED_UP_FREQ
            self.CURRENT_DOWN_FREQ = self.SAVED_DOWN_FREQ
            self.bcnbt._background_color = None
            ON_BEACON = False
            self.set_slider()
        else:
            # SAVED_UP_FREQ = CURRENT_UP_FREQ
            self.SAVED_DOWN_FREQ = self.CURRENT_DOWN_FREQ
            # CURRENT_UP_FREQ = CURRENT_SAT_CONFIG.get(
            #    "beacon", CURRENT_SAT_CONFIG["up_center"]
            # )
            self.CURRENT_DOWN_FREQ = self.CURRENT_SAT_CONFIG.get(
                "beacon", self.CURRENT_SAT_CONFIG["down_center"]
            )
            self.ON_BEACON = True
            self.bcnbt._background_color = RED
            self.set_slider(type="beacon")

    def start_stop(self):

        if self.RUN:
            self.RUN = False
            self.runbt._background_color = RED
        else:
            self.RUN = True
            self.RIG_UP = configure_rig(self.RIG_UP, self.RIG_UP.rig_num, self.CONFIG)
            self.RIG_DOWN = configure_rig(
                self.RIG_DOWN, self.RIG_DOWN.rig_num, self.CONFIG
            )
            self.runbt._background_color = GREEN
            self.RIG_UP.open()
            self.RIG_DOWN.open()

    def enable_rotator(self):
        if self.ROTATOR:
            self.ROTATOR = False
            self.ROT.set_position(0, 0)
            self.ROT.close()
            self.enablerot._background_color = None
        else:
            self.ROTATOR = True
            self.ROT.open()
            self.enablerot._background_color = GREEN

    def tune_center(self):
        self.CURRENT_UP_FREQ = self.CURRENT_SAT_CONFIG["up_center"]
        self.CURRENT_DOWN_FREQ = self.CURRENT_SAT_CONFIG["down_center"] + self.DIFF_FREQ
        self.set_slider()
        self.bcnbt._background_color = None

    def swap_rig(self):
        RIG_TEMP = self.RIG_DOWN
        q_temp = self.q_down
        self.RIG_DOWN = self.RIG_UP
        self.q_down = self.q_up
        self.RIG_UP = RIG_TEMP
        self.q_up = q_temp
        self.RIG_UP.set_mode(RIG_MODES[self.CURRENT_SAT_CONFIG["up_mode"]])
        self.RIG_DOWN.set_mode(RIG_MODES[self.CURRENT_SAT_CONFIG["down_mode"]])
        if self.RIG_UP.tone:
            self.RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)
            self.RIG_UP.set_ctcss_tone(
                RIG_VFOS[self.RIG_UP.vfo_name],
                self.RIG_UP.tone,
            )
        else:
            self.RIG_UP.set_func(Hamlib.RIG_FUNC_TONE, 1)

    def save_satlist(self):
        SAT_LIST[self.CURRENT_SAT_CONFIG["index"]]["saved_diff_freq"] = self.DIFF_FREQ
        with open("config/satlist.json", "w") as f:
            json.dump(SAT_LIST, f, indent=4)

    def change_freq(self, q, rig):
        while True:
            if rig.error_status != 0:
                rig.open()
                logger.warning(f"rig {rig.rig_name}: {rig.error_status}")

            freq = q.get()
            rig.set_freq(RIG_VFOS[rig.vfo_name], freq)
            q.task_done()

    def update_rotator(self, q, rot):
        while True:
            position = q.get()
            rot_azi, rot_ele = position
            rot.set_position(rot_azi, rot_ele)
            q.task_done()

    def lock_unlock_vfos(self):
        self.LOCKED = not self.LOCKED
        if self.LOCKED:
            self.lock_bt._background_color = None
            self.save_satlist()
        else:
            self.lock_bt._background_color = RED

    def mainloop(self, test: bool) -> None:
        observer = get_observer(self.CONFIG)
        pygame_icon = pygame.image.load("images/300px-DopplerSatScheme.bmp")
        pygame.display.set_icon(pygame_icon)
        radio_delay = pygame.time.get_ticks()
        radio_status_delay = pygame.time.get_ticks()
        rotator_delay = pygame.time.get_ticks()
        az_rangelist1 = self.CONFIG["observer_conf"]["range1"].split("-")
        az_rangelist2 = self.CONFIG["observer_conf"]["range2"].split("-")
        curr_rot_azi, curr_rot_ele = 0, 0
        rigupstatus = "??"
        rigdownstatus = "??"
        first_run = 5
        while True:
            if self.CURRENT_SAT_CONFIG["up_mode"] != "FM":
                sidestring = f"BCN {self.CURRENT_SAT_CONFIG.get('beacon',self.CURRENT_SAT_CONFIG['down_center']):,.0f}".replace(
                    ",", "."
                )
            else:
                sidestring = f"TONE {self.CURRENT_SAT_CONFIG.get('tone', None)}"
            self.main_menu.set_title(
                f"{self.CURRENT_SAT_CONFIG['display_name']} - {sidestring}"
            )

            (
                az,
                ele,
                shift_down,
                shift_up,
                shifted_down,
                shifted_up,
            ) = recalc_shift_and_pos(
                observer,
                self.CURRENT_SAT_OBJECT,
                self.CURRENT_UP_FREQ,
                self.CURRENT_DOWN_FREQ,
            )

            if self.ROTATOR:
                if pygame.time.get_ticks() - rotator_delay > 1000:
                    rot_azi = float(az)
                    rot_ele = 0.0
                    if float(ele) > -4 and (
                        rot_azi in range(int(az_rangelist1[0]), int(az_rangelist1[1]))
                        or (
                            rot_azi
                            in range(int(az_rangelist2[0]), int(az_rangelist2[1]))
                        )
                    ):
                        if float(ele) >= 0:
                            rot_ele = float(ele)
                        curr_rot_azi, curr_rot_ele = self.ROT.get_position()
                        logger.warning(f"tracking az {rot_azi} ele {rot_ele}")
                        # ROT.set_position(rot_azi, rot_ele)
                        rotator_delay = pygame.time.get_ticks()
                        if self.ROT.error_status != 0:
                            self.ROT.open()
                            curr_rot_azi, curr_rot_ele = 99, 99

                        self.q_rot.put((rot_azi, rot_ele))

                self.lock_bt.set_title(
                    f"Az {az}/{int(curr_rot_azi)} El {ele}/{int(curr_rot_ele)} {self.DIFF_FREQ}"
                )  # TXPWR {rf_level}%"

            else:
                self.lock_bt.set_title(
                    f"Az {az} El {ele} {self.DIFF_FREQ}"
                )  # TX {rf_level}%")
            if self.RUN:
                down_freq = self.RIG_DOWN.get_freq(RIG_VFOS[self.RIG_DOWN.vfo_name])
                temp_diff = self.CURRENT_DOWN_FREQ - (down_freq - shift_down)
                if abs(temp_diff) > 5 and first_run < 0:
                    # self.q_down.put(shifted_down - temp_diff)
                    # self.RIG_DOWN.set_freq(
                    #    RIG_VFOS[self.RIG_DOWN.vfo_name], shifted_down - temp_diff
                    # )
                    self.CURRENT_DOWN_FREQ = self.CURRENT_DOWN_FREQ - temp_diff
                    if self.LOCKED:
                        self.CURRENT_UP_FREQ = self.CURRENT_UP_FREQ + temp_diff
                        self.q_up.put(shifted_up - temp_diff)

                    print(temp_diff)
                else:
                    first_run -= 1
                    self.RIG_DOWN.set_freq(
                        RIG_VFOS[self.RIG_DOWN.vfo_name], shifted_down
                    )

                """if RIG_UP.error_status != 0:
                    logger.warning(f"rigup error: {RIG_UP.error_status}")
                    # RIG_UP = configure_rig(RIG_UP, RIG_UP.rig_num, CONFIG)

                if RIG_DOWN.error_status != 0:
                    logger.warning(f"rigdown error: {RIG_DOWN.error_status}")
                    # RIG_DOWN = configure_rig(RIG_DOWN, RIG_DOWN.rig_num, CONFIG)
                """
                if pygame.time.get_ticks() - radio_status_delay > 1500:
                    rigupstatus = RIG_STATUS[self.RIG_UP.error_status]
                    rigdownstatus = RIG_STATUS[self.RIG_DOWN.error_status]
                    radio_status_delay = pygame.time.get_ticks()
                if pygame.time.get_ticks() - radio_delay > 500:
                    self.q_up.put(shifted_up)
                    radio_delay = pygame.time.get_ticks()

            self.up_label1.set_title(
                f"UP: {self.CURRENT_UP_FREQ:,.0f} - {self.CURRENT_SAT_CONFIG['up_mode']} - {self.RIG_UP.rig_name}:{rigupstatus}".replace(
                    ",", "."
                ),
            )
            self.up_label2.set_title(
                f"UP: {shifted_up:,.0f} SHIFT: {abs(shift_up)}".replace(",", ".")
            )

            self.down_label1.set_title(
                f"DN: {self.CURRENT_DOWN_FREQ:,.0f} - {self.CURRENT_SAT_CONFIG['down_mode']} - {self.RIG_DOWN.rig_name}:{rigdownstatus}".replace(
                    ",", "."
                )
            )

            self.down_label2.set_title(
                f"DN: {shifted_down:,.0f} SHIFT: {abs(shift_down)}".replace(",", ".")
            )
            if self.CURRENT_UP_FREQ in range(
                self.CURRENT_SAT_CONFIG["up_start"], self.CURRENT_SAT_CONFIG["up_end"]
            ):
                self.RANGE_SLIDER_UP.set_value(self.CURRENT_UP_FREQ)

            if self.CURRENT_DOWN_FREQ in range(
                self.CURRENT_SAT_CONFIG["down_start"],
                self.CURRENT_SAT_CONFIG["down_end"],
            ):

                self.RANGE_SLIDER_DOWN.set_value(self.CURRENT_DOWN_FREQ)

                # Application events
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    exit()
                elif event.type == pygame.MOUSEWHEEL and event.y < 0:
                    self.CURRENT_DOWN_FREQ -= 1 * self.CONFIG["frequency_step"]
                    if self.LOCKED:
                        self.CURRENT_UP_FREQ += 1 * self.CONFIG["frequency_step"]
                    else:
                        self.DIFF_FREQ -= 1 * self.CONFIG["frequency_step"]

                elif event.type == pygame.MOUSEWHEEL and event.y > 0:
                    self.CURRENT_DOWN_FREQ += 1 * self.CONFIG["frequency_step"]
                    if self.LOCKED:
                        self.CURRENT_UP_FREQ -= 1 * self.CONFIG["frequency_step"]
                    else:
                        self.DIFF_FREQ += 1 * self.CONFIG["frequency_step"]

                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == self.CONFIG["mouse_buttons"]["lock_vfo"]
                ):
                    self.lock_unlock_vfos()

                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == self.CONFIG["mouse_buttons"]["tune_center"]
                ):
                    self.tune_center()
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == self.CONFIG["mouse_buttons"]["tune_beacon"]
                ):
                    self.tune_beacon()
                if DEBUG:
                    if event.type == pygame.MOUSEWHEEL:
                        #   logger.warning(event)
                        # logger.warning(event.x, event.y)
                        logger.warning(event.flipped)
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        print(f"pressed mouse button {event.button}")
                    # logger.warning(f"mouse event {event}")

            self.main_menu.update(events)
            self.main_menu.draw(self.surface)

            pygame.display.flip()


def main(test: bool = False) -> "App":
    """
    Main function.

    :param test: Indicate function is being tested
    :return: App object
    """
    app = App(args)
    app.mainloop(test)
    return app


if __name__ == "__main__":
    main()
