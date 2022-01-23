#%%
#%%
import sys

sys.path.append("/usr/local/lib/python3.9/site-packages/")
import Hamlib
import time

Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_VERBOSE)

my_rig = Hamlib.Rig(Hamlib.RIG_MODEL_NETRIGCTL)
my_rig.set_conf("rig_pathname", "localhost:4532")
my_rig.set_conf("retry", "5")
my_rig.open()
#%%
my_rig.set_vfo_opt(0)
my_rig.set_freq(Hamlib.RIG_VFO_CURR, 145000000)

# %%
