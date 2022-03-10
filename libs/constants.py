from .satlib import get_sat_list
import Hamlib
import pygame_menu


STEP = 50
H_SIZE = 320
W_SIZE = 480
SAT_LIST = get_sat_list()
RIG_STATUS = {
    -1: "ERR",
    0: "OK",
    -9: "ERR",
    -6: "ERR",
    -11: "ERR",
    -8: "ERR",
    -5: "ERR",
}
WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
DEFAULT_RIG_UP = 0
DEFAULT_RIG_DOWN = 1
MIN_ELE = -3
