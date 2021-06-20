#%%
from threading import Event

from gpiozero import RotaryEncoder, Button

rotor = RotaryEncoder(17, 18, max_steps=1, wrap=False)


x = 1

done = Event()


def show_num(r):
    print(r.steps)


rotor.when_rotated = show_num

done.wait()
