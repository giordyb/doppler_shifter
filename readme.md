# doppler_shifter 


doppler_shifter is a tool to adjust the frequencies of two radios via cat control based on the satellite's doppler shift in a portable setting.

It is designed to run on a raspberry pi with a ~~4x20 lcd screen connected via i2c and a rotary encoder via GPIOs~~ (old version, it looked like [this](https://github.com/giordyb/doppler_shifter/raw/main/images/oldversion.JPG)) 3.5in [LCD TouchScreen](http://www.lcdwiki.com/3.5inch_RPi_Display) and it can be controlled with a mouse. The mouse is needed to control some of the functions (switch to the beacon frequency, go back to the center, unlock the VFOs), etc) via the buttons and control the frequency adjustment with the mouse wheel.

![doppler_shifter](./images/newversion.jpg?raw=true)


It supports any rig compatible with Hamlib

![here is a video of it running](./images/usage.gif?raw=true)

[here are the install instructions](https://github.com/giordyb/doppler_shifter/blob/5015b8ee5b41cb8cf3b3a181e51b40ee519a29c2/install.md)


# usage

* turn on the raspberry pi
* select the satellite by clicking on the Sats menu
* after selecting the satellite the uplink and downlink frequencies will be set, starting in the middle of the band (for linear sats). the frequencies are taken from [ke0bpr frequency cheat sheet](https://ke0pbr.wordpress.com/2018/12/31/my-frequency-cheat-sheet/)
* on the display you will see the following info (for both uplink and downlink):
    * the satellite name and beacon frequency
    * the current azimuth and elevation of the satellite, if the VFOs are locked and the power of the rig (needed when lowering the tx power to avoid de-sense) 
    * the uplink frequency you want to be tuned to, the mode and the status of the connection to the rig
    * the actual uplink tuned frequency (doppler shift adjusted) and the doppler shift 

* the uplink and downlink frequencies are locked together based on the table of the cheat sheet. rotating the mouse wheel will increase the uplink frequency and decrease the downlink frequency

* you can only tune up or down within the limits of the passband of the satellite (set in the satlist.json file)

* if you press one of the mouse buttons (configured in the code) the uplink and downlink frequencies will be unlocked and only the uplink frequency will change when moving the mouse scroll wheel. This is needed to finely tune the relationship between the uplink and downlink. If anyone has any idea on how to automate this please let me know
