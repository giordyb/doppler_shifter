import Hamlib

from multiprocessing import Queue
import time
import os
import logging

RIG_MODES = {
    "FM": Hamlib.RIG_MODE_FM,
    "AM": Hamlib.RIG_MODE_AM,
    "USB": Hamlib.RIG_MODE_USB,
    "LSB": Hamlib.RIG_MODE_LSB,
}

RIG_VFOS = {
    "VFOA": Hamlib.RIG_VFO_A,
    "VFOB": Hamlib.RIG_VFO_B,
    "VFO": Hamlib.RIG_VFO_CURR,
}
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
logger = logging.getLogger(__name__)


class RigWrapper:
    def __init__(self, CONFIG, rignum) -> None:

        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)
        self.rig = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
        self.lastfreq = 0
        self.rig.set_conf("retry", "1")
        rig_pathname = (
            f"{CONFIG['rigs'][rignum]['hostname']}:{CONFIG['rigs'][rignum]['port']}"
        )

        self.rig.set_conf(
            "rig_pathname",
            rig_pathname,
        )
        self.rig.rig_name = CONFIG["rigs"][rignum]["rig_name"]
        self.rig.vfo_name = CONFIG["rigs"][rignum]["vfo_name"]
        self.rig.rig_num = rignum
        self.rig.tone = 0
        self.rig.open()

    def set_freq(self, freq):
        if abs(self.lastfreq - freq) >= 10:
            self.rig.set_freq(RIG_VFOS[self.rig.vfo_name], freq)
            self.lastfreq = freq

    def set_mode(self, mode):
        self.rig.set_mode(RIG_MODES[mode])

    def set_tone(self, tone):
        if tone == "0.0":
            self.rig.set_func(Hamlib.RIG_FUNC_TONE, 0)
            self.rig.tone = False
        else:
            self.rig.set_func(Hamlib.RIG_FUNC_TONE, 1)
            self.rig.set_ctcss_tone(
                RIG_VFOS[self.rig.vfo_name],
                int(tone.replace(".", "")),
            )

    def set_ts(self, step):
        self.rig.set_ts(RIG_VFOS[self.rig.vfo_name], step)


def rig_loop(q, status_q, CONFIG, name):
    while True:
        try:
            status_q.put(RIG.rig.error_status)
        except:
            status_q.put(99)
        # if not q.empty():
        queue_values = q.get()
        # if DEBUG:
        #    print(queue_values, name)

        if isinstance(queue_values, tuple):
            command, value = queue_values
            if command == "config":
                RIG = RigWrapper(CONFIG, value)
                print(RIG.rig.error_status)
            elif command == "freq":
                RIG.set_freq(value)
            elif command == "mode":
                RIG.set_mode(value)
            elif command == "tone":
                RIG.set_tone(value)
