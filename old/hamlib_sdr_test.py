#%%
import time
import sys
import os

sys.path.append("/usr/local/lib/python3.9/site-packages/")
import Hamlib

Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_VERBOSE)

my_rig = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
my_rig.set_conf("rig_pathname", "localhost:4532")
my_rig.set_conf("retry", "5")
#%%
my_rig.open()
my_rig.get_vfo()
my_rig.set_vfo(Hamlib.RIG_VFO_CURR)
my_rig.set_freq(Hamlib.RIG_VFO_CURR, "144000000")
# %%
