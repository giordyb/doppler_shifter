# doppler_shifter 


doppler_shifter is a tool to adjust the frequencies of two radios via cat control based on the satellite's doppler shift in a portable setting
it is designed to run on a raspberry pi with a ~~4x20 lcd screen connected via i2c and a rotary encoder via GPIOs (old version, it looked like [this]()~~ 3.5in [LCD Screen](http://www.lcdwiki.com/3.5inch_RPi_Display)  

The LCD and rotary tool

![lcd and rotary tool](./lcd.jpg?raw=true "lcd and rotary tool")

doppler shifter controlling a Kenwood TH-D74 and a Icom IC-705

![running](./image1.png?raw=true "running")


it supports any rig compatible with Hamlib

[here is a video of it running](https://youtu.be/zTdj3pQJ4dA)

[here are the install instructions](https://github.com/giordyb/doppler_shifter/blob/5015b8ee5b41cb8cf3b3a181e51b40ee519a29c2/install.md)

* added feature: turning the rotary wheel while pressing it will change only the uplink frequency



# usage

* turn on the device and follow the setup steps
* select the satellite, using the rotary control to scroll through the list
* after selecting the satellite the uplink and downlink frequencies will be set, starting in the middle of the band (for linear sats). the frequencies are taken from [ke0bpr frequency cheat sheet](https://ke0pbr.wordpress.com/2018/12/31/my-frequency-cheat-sheet/)
* on the display you will see the following info (for both uplink and downlink):
    * the frequency you want to be tuned to.
    * the frequency's doppler shift
    * the actual tuned frequency, with the doppler shift added or subtracted
    * the mode (USB/LSB/FM)
    * the az and el of the satellite (in °)
* the uplink and downlink frequencies are locked together based on the table of the cheat sheet. rotating clockwise will increase the uplink frequency and decrease the downlink frequency by the rotary_step parameter set in the config.json
* you can only tune up or down within the limits of the passband of the satellite (set in the satlist.py file)
* if you press the rotary button the uplink and downlink frequencies will be unlocked (you will see an open lock icon appear on the 2nd line of the display instead of the up arrows) and only the uplink frequency will change when moving the rotary control. Just press the rotary button again to lock. This is needed to finely tune the relationship between the uplink and downlink. If anyone has any idea on how to automate this please tell...
* if you press the rotary control for more than 20 seconds the program will let you select another satellite