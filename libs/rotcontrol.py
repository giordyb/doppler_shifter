from multiprocessing import Queue
import Hamlib


class RotWrapper:
    def __init__(self, CONFIG) -> None:

        Hamlib.rot_set_debug(Hamlib.RIG_DEBUG_NONE)
        self.rot = Hamlib.Rot(Hamlib.ROT_MODEL_NETROTCTL)

        self.rot.set_conf("retry", "1")
        rot_pathname = f"{CONFIG['rotator']['hostname']}:{CONFIG['rotator']['port']}"
        self.rot.set_conf("rot_pathname", rot_pathname)
        self.rot.open()

    def set_freq(self, freq):
        if abs(self.lastfreq - freq) >= 10:
            self.rot.set_freq(rot_VFOS[self.rig.vfo_name], freq)
            self.lastfreq = freq


def rot_loop(q, status_q, CONFIG):
    while True:
        if not q.empty():
            queue_values = q.get()
            try:
                status_q.put(ROT.rig.error_status)
            except:
                status_q.put(99)
            if tuple(queue_values):
                command, value = queue_values
                if command == "config":
                    RIG = RotWrapper(CONFIG, value)
                    print(RIG.rig.error_status)
                if command == "position":
                    RIG.set_freq(value)
                if command == "mode":
                    RIG.set_mode(value)
                if command == "tone":
                    RIG.set_tone(value)
            # q.task_done()
