from .satlib import get_sat_list, load_conf
import Hamlib
import pygame_menu

RIG_MODES = {
    "FM": Hamlib.RIG_MODE_FM,
    "AM": Hamlib.RIG_MODE_AM,
    "USB": Hamlib.RIG_MODE_USB,
    "LSB": Hamlib.RIG_MODE_LSB,
}

RIG_VFOS = {"VFOA": Hamlib.RIG_VFO_A, "VFOB": Hamlib.RIG_VFO_B}


STEP = 50
H_SIZE = 320
W_SIZE = 480
SAT_LIST = get_sat_list()
CONFIG = load_conf()
RIG_STATUS = {-1: "ERR", 0: "OK", -9: "ERR", -6: "ERR", -11: "ERR", -8: "ERR"}
WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)
