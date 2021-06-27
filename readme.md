# doppler_shifter 


doppler_shifter is a tool to adjust the frequencies of two radios via cat control based on the satellite's doppler shift in a portable setting
it is designed to run on a raspberry pi with a 4x20 lcd screen connected via i2c and a rotary encoder via GPIOs

many thanks to https://github.com/Marzona for providing already made Python libs to connect to rigctld and sends commands

The LCD and rotary tool

![lcd and rotary tool](./lcd.jpg?raw=true "lcd and rotary tool")

doppler shifter controlling a Kenwood TH-D74 and a Icom IC-705

![running](./image1.png?raw=true "running")


it supports any rig compatible with Hamlib

[here is a video of it running](https://youtu.be/zTdj3pQJ4dA)

[here are the install instructions](https://github.com/giordyb/doppler_shifter/blob/5015b8ee5b41cb8cf3b3a181e51b40ee519a29c2/install.md)

* added feature: turning the rotary wheel while pressing it will change only the uplink frequency