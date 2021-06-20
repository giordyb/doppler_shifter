#%%
import rigctllib

#%%
rig705_config = {}
rig705_config["hostname"] = "localhost"
rig705_config["port"] = 4532
rig705_config["rig_number"] = 1
rig705 = rigctllib.RigCtl(rig705_config)
rig705.set_mode(mode="LSB")


#%%
import rigctllib

rigd74_config = {}
rigd74_config["hostname"] = "localhost"
rigd74_config["port"] = 4533
rigd74_config["rig_number"] = 2
rigd74 = rigctllib.RigCtl(rigd74_config)
d74_init = None
while d74_init != "RPRT 0":
    d74_init = rigd74.set_vfo("VFOB")
# rigd74.set_mode(mode="USB", vfo="2")
rigd74.set_frequency(145390000)

#%%

print(f"rig1 {rig1.get_frequency()} rig2 {rig2.get_frequency()}")
rig1.set_frequency(145390000)
print(f"rig1 {rig1.get_frequency()} rig2 {rig2.get_frequency()}")

print(f"rig1 {rig1.get_frequency()} rig2 {rig2.get_frequency()}")
print(f"rig1 {rig1.get_frequency()} rig2 {rig2.get_frequency()}")
# %%
