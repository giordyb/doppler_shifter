from multiprocessing import Queue
import Hamlib
import logging

logger = logging.getLogger(__name__)

import time


class RotWrapper:
    def __init__(self, CONFIG) -> None:

        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)
        self.rot = Hamlib.Rot(Hamlib.ROT_MODEL_NETROTCTL)

        self.rot.set_conf("retry", "1")
        rot_pathname = f"{CONFIG['rotator']['hostname']}:{CONFIG['rotator']['port']}"
        self.rot.set_conf("rot_pathname", rot_pathname)
        self.rot.open()

    def set_position(self, position):
        logger.warning(f"setting position {position}")
        azi, ele = position
        try:
            self.rot.set_position(azi, ele)
        except:
            logger.warning("crash")
        # logger.warning(f"got position {self.rot.get_position()}")

    def get_position(self):
        # logger.warning(f"sending rotator position {self.rot.get_position()}")
        return self.rot.get_position()


def rot_loop(q, position_q, CONFIG):
    while True:

        queue_values = None
        if not q.empty():
            queue_values = q.get()
        if isinstance(queue_values, tuple):
            command, value = queue_values
            if command == "config":
                ROT = RotWrapper(CONFIG)
                logger.warning(ROT.rot.error_status)
            elif command == "set_position":
                ROT.set_position(value)
            elif command == "get_position":
                try:
                    status = ROT.rot.error_status
                    if status != 0:
                        raise
                    position_q.put(ROT.get_position())
                except:
                    position_q.put((99, 99))
