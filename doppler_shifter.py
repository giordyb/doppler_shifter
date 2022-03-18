__all__ = ["main"]
import sys
import os
import logging
import subprocess
import argparse
import json
import datetime
import pandas as pd
import ephem
import matplotlib.pyplot as plt
import matplotlib
from pygame_menu.locals import ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT
from pygame_menu.events import RESET, BACK

matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg

import numpy as np

# from queue import Queue

from multiprocessing import Process, Queue

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
from libs.rigcontrol import rig_loop
from libs.rotcontrol import rot_loop
from libs.satlib import get_satellite, save_conf, update_tles, get_observer, load_conf
from libs.commonlib import (
    create_slider,
    recalc_shift_and_pos,
    restart_rig,
    shutdown,
)
from libs.constants import (
    H_SIZE,
    W_SIZE,
    SAT_LIST,
    RIG_STATUS,
    WHITE,
    RED,
    GREEN,
    DEFAULT_RIG_UP,
    DEFAULT_RIG_DOWN,
    MIN_ELE,
    QUEUE_MAXSIZE,
    BUTTON_FONT_SIZE,
    WIDGET_FONT_SIZE,
)

from pygame.locals import Color
from pygame_menu.widgets.core.widget import Widget

from random import randrange
from typing import List, Tuple, Optional

from string import Template


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = "{:02d}".format(hours)
    d["M"] = "{:02d}".format(minutes)
    d["S"] = "{:02d}".format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


all_args = argparse.ArgumentParser()
all_args.add_argument(
    "-c",
    "--configpath",
    required=False,
    help="config file path",
    default="config/config.json",
)
args = vars(all_args.parse_args())


def pygame2matplotlib(w, h):
    return {"figsize": (w, h), "dpi": 1}


class PolarChart(object):
    dpi = 65
    inch = 4
    previous_rotor_points = None
    previous_current_points = None

    def __init__(self, main_menu) -> None:
        self.fig, self.ax = plt.subplots(subplot_kw={"projection": "polar"})
        self.fig.set_dpi(self.dpi)
        self.ax.set_xticklabels([])
        self.fig.set_size_inches(self.inch, self.inch)
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        self.ax.grid(True)
        self.fig.patch.set_visible(False)
        self.canvas = agg.FigureCanvasAgg(self.fig)
        self.canvas.draw()
        renderer = self.canvas.get_renderer()
        raw_data = renderer.buffer_rgba()
        surf = pygame.image.frombuffer(
            raw_data, (self.inch * self.dpi, self.inch * self.dpi), "RGBA"
        )
        sur = main_menu.add.surface(surf, float=True)
        sur.translate(440, -425)
        self.plt = plt

    def fix_axis(self):
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        self.ax.set_rlim(bottom=-5, top=90)
        self.ax.set_yticks(np.arange(-5, 91, 15))
        self.ax.set_yticklabels(self.ax.get_yticks()[::-1])

    def plot_next(self, CURRENT_SAT_OBJECT, observer, aos, los):
        self.ax.cla()
        sat_alt, sat_az = [], []
        sat_dates = pd.date_range(
            str(aos),
            str(los),
            periods=30,
        ).tolist()
        for date in sat_dates:
            observer.date = date
            CURRENT_SAT_OBJECT.compute(observer)

            sat_az.append(CURRENT_SAT_OBJECT.az)
            sat_alt.append(np.rad2deg(CURRENT_SAT_OBJECT.alt))  # type: ignore
        self.fix_axis()
        colormap = plt.get_cmap("autumn")

        self.ax.scatter(
            sat_az, 90 - np.array(sat_alt), cmap=colormap, c=range(0, len(sat_alt))
        )
        self.canvas.draw()

    def plot_current(self, curr_az, curr_el):
        if isinstance(self.previous_current_points, List):
            for point in self.previous_current_points:
                point.remove()
        self.previous_current_points = self.ax.plot(
            curr_az, 90 - np.rad2deg(curr_el), color="green", marker="o", markersize=10  # type: ignore
        )
        self.canvas.draw()

    def plot_rotator(self, rotor_az, rotor_el):
        if isinstance(self.previous_rotor_points, List):
            for point in self.previous_rotor_points:
                point.remove()
        self.previous_rotor_points = self.ax.plot(
            np.deg2rad(rotor_az), 90 - rotor_el, color="blue", marker="s", markersize=10  # type: ignore
        )
        self.canvas.draw()


class Rig(object):
    tone = 0

    def __init__(self, name, CONFIG) -> None:
        self.rig_name = name
        self.q = Queue(maxsize=QUEUE_MAXSIZE)
        self.status_q = Queue(maxsize=QUEUE_MAXSIZE)
        """self.thread = Thread(
            target=rig_loop, args=(self.q, self.status_q, CONFIG, name)
        )
        self.thread.setDaemon(True)
        self.thread.start()"""
        self.process = Process(
            target=rig_loop, args=(self.q, self.status_q, CONFIG, name)
        )
        self.process.daemon = True
        self.process.start()


class Rot(object):
    def __init__(self, CONFIG) -> None:
        self.q = Queue(maxsize=QUEUE_MAXSIZE)
        self.position_q = Queue(maxsize=QUEUE_MAXSIZE)
        self.process = Process(target=rot_loop, args=(self.q, self.position_q, CONFIG))
        self.process.daemon = True
        self.process.start()


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
    AOS = None
    LOS = None

    def __init__(self, args) -> None:
        self.CONFIG = load_conf(args["configpath"])
        self.CURRENT_SAT_CONFIG = SAT_LIST[self.CONFIG.get("loaded_sat", 0)]
        update_tles(self.CONFIG["sat_url"])
        self.surface: Optional["pygame.Surface"] = None
        # self.CURRENT_SAT_OBJECT = get_satellite(self.CURRENT_SAT_CONFIG)

        self.RIG_UP = Rig("FT-818", self.CONFIG)
        self.RIG_UP.q.put(("config", DEFAULT_RIG_UP))
        self.RIG_DOWN = Rig("IC-705", self.CONFIG)
        self.RIG_DOWN.q.put(("config", DEFAULT_RIG_DOWN))
        self.ROT = Rot(self.CONFIG)
        self.ROT.q.put(("config", None))

        self.RANGE_SLIDER_UP = create_slider(self.CURRENT_SAT_CONFIG, "up")
        self.RANGE_SLIDER_DOWN = create_slider(self.CURRENT_SAT_CONFIG, "down")

        # Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)

        # rotator_thread = Thread(target=self.update_rotator, args=(self.q_rot, self.ROT))
        # rotator_thread.setDaemon(True)
        # rotator_thread.start()

        self.surface = create_example_window(
            "Sat", (W_SIZE, H_SIZE), flags=pygame.FULLSCREEN
        )

        common_theme = pygame_menu.themes.THEME_DEFAULT.copy()  # type: ignore
        common_theme.title_font_size = 30
        common_theme.font = pygame_menu.font.FONT_FIRACODE  # type: ignore
        common_theme.widget_font_size = WIDGET_FONT_SIZE
        common_theme.widget_alignment = ALIGN_LEFT
        common_theme.title_bar_style = (
            pygame_menu.widgets.MENUBAR_STYLE_TITLE_ONLY_DIAGONAL  # type: ignore
        )

        self.sat_menu = pygame_menu.Menu(
            height=H_SIZE,
            onclose=RESET,
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

        # self.satselector.

        self.gpslabel = self.sat_menu.add.label("None")
        self.sat_menu.add.vertical_margin(30)
        self.sat_menu.add.button("Return to Menu", BACK)  # type: ignore
        self.sat_menu.add.button("Shutdown", shutdown)
        self.sat_menu.add.button("Quit", self.quit)

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
                (x["rig_name"], ind, None, "up")
                for ind, x in enumerate(self.CONFIG["rigs"])
            ],
            onchange=self.change_rig,
            selection_box_height=5,
            default=0,
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
                (x["rig_name"], ind, None, "down")
                for ind, x in enumerate(self.CONFIG["rigs"])
            ],
            onchange=self.change_rig,
            selection_box_height=5,
            default=1,
        )
        self.radio_menu.add.vertical_margin(25)
        self.radio_menu.add.button("Return to Menu", BACK)  # type: ignore

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
            rows=9,
            touchscreen=True,
            overflow=(False, False),
        )

        self.coordinates = self.main_menu.add.label(
            title="", align=ALIGN_LEFT, padding=0  # type: ignore
        )
        self.main_menu.add.clock(
            # font_size=30,
            # font_name=pygame_menu.font.FONT_DIGITAL,
            padding=0,
        )

        self.aos_los_label = self.main_menu.add.label(
            title="",
            align=ALIGN_LEFT,
            padding=0,
            # font_name=pygame_menu.font.FONT_DIGITAL,
            # font_size=30,
        )
        self.up_label1 = self.main_menu.add.label(
            title="", align=ALIGN_LEFT, padding=0  # type: ignore
        )
        self.up_label2 = self.main_menu.add.label(
            title="", align=ALIGN_LEFT, padding=0  # type: ignore
        )
        self.down_label1 = self.main_menu.add.label(
            title="", align=ALIGN_LEFT, padding=0  # type: ignore
        )
        self.down_label2 = self.main_menu.add.label(
            title="", align=ALIGN_LEFT, padding=0  # type: ignore
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
        self.polar = PolarChart(self.main_menu)
        self.sat_bt = self.main_menu.add.button(
            self.sat_menu.get_title(),
            self.sat_menu,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )

        self.radiobt = self.main_menu.add.button(
            self.radio_menu.get_title(),
            self.radio_menu,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )
        self.bcnbt = self.main_menu.add.button(
            "Beacon",
            self.tune_beacon,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )
        self.centerbt = self.main_menu.add.button(
            "Center",
            self.tune_center,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )

        self.enablerot = self.main_menu.add.button(
            "Rotator Off",
            self.enable_rotator,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )
        self.enablerot._background_color = RED
        self.runbt = self.main_menu.add.button(
            "Track Off",
            lambda: self.start_stop(),
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )
        self.runbt._background_color = RED
        self.lockbutton = self.main_menu.add.button(
            f"Lock {self.DIFF_FREQ}",
            self.lock_unlock_vfos,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )

        self.swapbt = self.main_menu.add.button(
            "swap",
            self.swap_rig,
            align=ALIGN_RIGHT,
            font_size=BUTTON_FONT_SIZE,
        )

        self.change_sat(("", self.CONFIG.get("loaded_sat", 0)), self.CURRENT_SAT_CONFIG)

    def change_rig(self, rigtuple, rigidx, RIG, side):
        rigdata, rigidx = rigtuple
        self.change_sat(("", self.CONFIG.get("loaded_sat", 0)), self.CURRENT_SAT_CONFIG)

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

    def quit(self):
        self.CONFIG["loaded_sat"] = self.CURRENT_SAT_CONFIG["index"]
        save_conf(args["configpath"], self.CONFIG)
        pygame.quit()

    def change_sat(self, satargs, newsat):
        global args
        satinfo, satindex = satargs
        self.CURRENT_SAT_CONFIG = newsat
        self.CURRENT_SAT_CONFIG["index"] = satindex
        self.CURRENT_SAT_OBJECT = get_satellite(newsat)
        self.CURRENT_UP_FREQ = self.CURRENT_SAT_CONFIG["up_center"]
        self.CURRENT_DOWN_FREQ = self.CURRENT_SAT_CONFIG["down_center"]
        self.DIFF_FREQ = self.CURRENT_SAT_CONFIG.get("saved_diff_freq", 0)
        self.RIG_UP.q.put(("mode", self.CURRENT_SAT_CONFIG["up_mode"]))
        self.RIG_DOWN.q.put(("mode", self.CURRENT_SAT_CONFIG["down_mode"]))

        if self.CURRENT_SAT_CONFIG["up_mode"] == "FM":
            if self.CURRENT_SAT_CONFIG["tone"] == "0.0":
                self.RIG_UP.q.put(("tone", "0.0"))
                self.RIG_UP.tone = 0
            else:
                self.RIG_UP.q.put(("tone", self.CURRENT_SAT_CONFIG["tone"]))
                self.RIG_UP.tone = int(self.CURRENT_SAT_CONFIG["tone"].replace(".", ""))
        else:
            self.RIG_DOWN.q.put(("step", self.CONFIG["frequency_step"]))
            self.RIG_UP.q.put(("tone", "0.0"))
            self.RIG_UP.tone = 0

        self.set_slider()
        self.CONFIG["loaded_sat"] = self.CURRENT_SAT_CONFIG["index"]
        observer, _ = get_observer(self.CONFIG)
        observer.date = datetime.datetime.utcnow()
        self.CURRENT_SAT_OBJECT.compute(observer)
        next_pass = observer.next_pass(self.CURRENT_SAT_OBJECT, singlepass=True)
        self.AOS = next_pass[0]
        self.LOS = next_pass[4]

        self.polar.plot_next(
            self.CURRENT_SAT_OBJECT, observer, next_pass[0], next_pass[4]
        )

    def tune_beacon(self):
        print("beacon")
        if self.ON_BEACON:
            # CURRENT_UP_FREQ = SAVED_UP_FREQ
            self.CURRENT_DOWN_FREQ = self.SAVED_DOWN_FREQ
            self.bcnbt._background_color = None
            self.ON_BEACON = False
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
            self.runbt.set_title("Track Off")
        else:
            self.RUN = True
            self.runbt._background_color = GREEN
            self.runbt.set_title("Track On")

    def enable_rotator(self):
        if self.ROTATOR:
            self.ROTATOR = False
            self.ROT.q.put(("set_position", (0, 0)))
            self.enablerot._background_color = RED
            self.enablerot.set_title("Rotator Off")
        else:
            self.ROTATOR = True
            self.enablerot._background_color = GREEN
            self.enablerot.set_title("Rotator On")

    def tune_center(self):
        self.CURRENT_UP_FREQ = self.CURRENT_SAT_CONFIG["up_center"]
        self.CURRENT_DOWN_FREQ = self.CURRENT_SAT_CONFIG["down_center"] + self.DIFF_FREQ
        self.set_slider()
        self.bcnbt._background_color = None

    def swap_rig(self):
        RIG_TEMP = self.RIG_DOWN
        self.RIG_DOWN = self.RIG_UP
        self.RIG_UP = RIG_TEMP
        self.RIG_UP.q.put(("mode", self.CURRENT_SAT_CONFIG["up_mode"]))
        self.RIG_DOWN.q.put(("mode", self.CURRENT_SAT_CONFIG["down_mode"]))
        if self.RIG_DOWN.tone:
            self.RIG_UP.q.put(("tone", self.CURRENT_SAT_CONFIG["tone"]))

    def save_satlist(self):
        SAT_LIST[self.CURRENT_SAT_CONFIG["index"]]["saved_diff_freq"] = self.DIFF_FREQ
        with open("config/satlist.json", "w") as f:
            json.dump(SAT_LIST, f, indent=4)

    def lock_unlock_vfos(self):
        self.LOCKED = not self.LOCKED
        if self.LOCKED:
            self.lockbutton._background_color = None
            self.save_satlist()
        else:
            self.lockbutton._background_color = RED

    def mainloop(self, test: bool) -> None:

        observer, is_gps = get_observer(self.CONFIG)
        self.gpslabel.set_title(  # type: ignore
            f"GPS LOCK: {is_gps} LAT:{round(observer.lat/ephem.degree,4)} LON:{round(observer.lon/ephem.degree,4)}"
        )
        pygame_icon = pygame.image.load("images/300px-DopplerSatScheme.bmp")
        pygame.display.set_icon(pygame_icon)
        az_rangelist1 = self.CONFIG["observer_conf"]["range1"].split("-")
        az_rangelist2 = self.CONFIG["observer_conf"]["range2"].split("-")
        rotator_delay = pygame.time.get_ticks()
        curr_rot_azi, curr_rot_ele = 0, 0
        rigupstatus = "??"
        rigdownstatus = "??"

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
                aos_remaining,
                los_remaining,
            ) = recalc_shift_and_pos(
                observer,
                self.CURRENT_SAT_OBJECT,
                self.CURRENT_UP_FREQ,
                self.CURRENT_DOWN_FREQ,
                self.AOS,
                self.LOS,
            )
            # self.plot_satellite(observer, az, ele)
            az_deg = round(np.rad2deg(az))  # type: ignore
            ele_deg = round(np.rad2deg(ele))  # type: ignore

            if self.ROTATOR:
                if pygame.time.get_ticks() - rotator_delay > 1000:
                    if not self.ROT.position_q.empty():
                        curr_rot_azi, curr_rot_ele = self.ROT.position_q.get()
                        self.polar.plot_rotator(curr_rot_azi, curr_rot_ele)
                    else:
                        self.ROT.q.put(("get_position", None), block=True)
                    rot_azi = az_deg
                    rot_ele = 0.0
                    if ele_deg > MIN_ELE and (
                        rot_azi in range(int(az_rangelist1[0]), int(az_rangelist1[1]))
                        or (
                            rot_azi
                            in range(int(az_rangelist2[0]), int(az_rangelist2[1]))
                        )
                    ):
                        if ele_deg >= 0:
                            rot_ele = ele_deg

                        logger.warning(f"tracking az {rot_azi} ele {rot_ele}")
                        self.ROT.q.put(("set_position", (rot_azi, rot_ele)), block=True)
                    rotator_delay = pygame.time.get_ticks()

                self.coordinates.set_title(  # type: ignore
                    f"Az {az_deg}/{int(curr_rot_azi)} El {ele_deg}/{int(curr_rot_ele)}"
                )

            else:
                self.coordinates.set_title(  # type: ignore
                    f"Az {az_deg} El {ele_deg}"
                )  # TX {rf_level}%")
            if ele_deg > 0:
                self.polar.plot_current(az, ele)
            self.lockbutton.set_title(f"Lock {self.DIFF_FREQ}")
            self.aos_los_label.set_title(  # type: ignore
                f"AOS {strfdelta(aos_remaining,'%H:%M:%S')} - LOS {strfdelta(los_remaining,'%H:%M:%S')}"
            )
            if self.RUN:
                self.RIG_DOWN.q.put(("freq", shifted_down))
                self.RIG_UP.q.put(("freq", shifted_up))
                if not self.RIG_UP.status_q.empty():
                    rigupstatus = RIG_STATUS.get(self.RIG_UP.status_q.get())
                if not self.RIG_DOWN.status_q.empty():
                    rigdownstatus = RIG_STATUS.get(self.RIG_DOWN.status_q.get())

            self.up_label1.set_title(  # type: ignore
                f"UP: {self.CURRENT_UP_FREQ:,.0f} - {self.CURRENT_SAT_CONFIG['up_mode']} - {self.RIG_UP.rig_name}:{rigupstatus}".replace(
                    ",", "."
                ),
            )
            self.up_label2.set_title(  # type: ignore
                f"UP: {shifted_up:,.0f} SHIFT: {abs(shift_up)}".replace(",", ".")
            )

            self.down_label1.set_title(  # type: ignore
                f"DN: {self.CURRENT_DOWN_FREQ:,.0f} - {self.CURRENT_SAT_CONFIG['down_mode']} - {self.RIG_DOWN.rig_name}:{rigdownstatus}".replace(
                    ",", "."
                )
            )

            self.down_label2.set_title(  # type: ignore
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
                    self.CONFIG["loaded_sat"] = self.CURRENT_SAT_CONFIG["index"]
                    save_conf(args["configpath"], self.CONFIG)
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
