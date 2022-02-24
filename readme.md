# doppler_shifter by IU2OZH


doppler_shifter is a tool to adjust the frequencies of two radios via cat control based on the satellite's doppler shift in a portable setting.

It is designed to run on a raspberry pi with a ~~4x20 lcd screen connected via i2c and a rotary encoder via GPIOs~~ (old version, it looked like [this](https://github.com/giordyb/doppler_shifter/raw/main/images/oldversion.JPG)) 3.5in [LCD TouchScreen](http://www.lcdwiki.com/3.5inch_RPi_Display) and it can be controlled with a mouse. The mouse is needed to control some of the functions (switch to the beacon frequency, go back to the center, unlock the VFOs), etc) via the buttons and control the frequency adjustment with the mouse wheel.

![doppler_shifter](./images/doppler_shifter_raspberry.jpg?raw=true)


It supports any rig compatible with Hamlib

![here is a video of it running](./images/usage.gif?raw=true)

[install instructions](https://github.com/giordyb/doppler_shifter/blob/5015b8ee5b41cb8cf3b3a181e51b40ee519a29c2/install.md)


# usage

* turn on the raspberry pi
* select the satellite by clicking on the Sats menu
* after selecting the satellite the uplink and downlink frequencies will be set, starting in the middle of the band (for linear sats). the frequencies are taken from [ke0bpr frequency cheat sheet](https://ke0pbr.wordpress.com/2018/12/31/my-frequency-cheat-sheet/)
* select the radio configuration (see the config file for examples)
* on the display you will see the following info (for both uplink and downlink):
    * the satellite name and beacon frequency
    * the current azimuth and elevation of the satellite, if the VFOs are locked and the power of the rig (needed when lowering the tx power to avoid de-sense) 
    * the uplink frequency you want to be tuned to, the mode and the status of the connection to the rig
    * the actual uplink tuned frequency (doppler shift adjusted) and the doppler shift 

* the uplink and downlink frequencies are locked together based on the table of the cheat sheet. moving the mouse wheel in either direction will increase/decrease the uplink frequency and decrease/increase the downlink frequency.

* the two sliders will show where you are in respect to the passband of the transponder (if you have selected a linear sat, in FM mode the sliders are hidden)

* the mouse buttons can be configured in the config file to respond to the following functions
    * lock/unlock the two VFOs
    * switch to the beacon frequency
    * switch to the center frequency

# features

- synchronizes the VFOs of 2 radios in inverting mode (when the rx frequency is increased the tx frequency is decreased) and can manage the frequency changes via a mouse wheel
- auto corrects for doppler shifts
- can automatically configure the PL tone for FM satellites
- based on the time, position and the downloaded TLEs can display the real time azimuth and elevation of the satellite
- can send the posizione of the satellite to an antenna rotor (compatible with hamlib) in order to track it
- automatically downloads TLEs from celestrak
- can manage a customized list of satellite and keep track of passband frequencies and configurations 
- lets you save the frequency corrections between uplink and downlink for each satellite
- if GPS is present can configure the position and time automatically

