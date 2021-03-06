from .satlib import get_sat_list
import Hamlib
import pygame_menu


W_SIZE = 800
H_SIZE = 600
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
QUEUE_MAXSIZE = 0
BUTTON_FONT_SIZE = 32
WIDGET_FONT_SIZE = 32
DEFAULT_ROTATOR_POSITION = (180, 0)
DEFAULT_CORRECTION_STEP_SIZE = 50
