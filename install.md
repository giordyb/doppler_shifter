
# hardware needed

1. a raspberry pi (tested on a 3b and 4b) with an sd card and raspbian installed
2. a 3.5in [LCD touch screen](http://www.lcdwiki.com/3.5inch_RPi_Display
)
3. a mouse with a few extra buttons (like the [Logitech MX Anywhere 3](https://www.logitech.com/en-us/products/mice/mx-anywhere-3-for-business.910-006215.html) )

# hardware setup
1. connect the LCD Touchscreen to the raspberry pi and install the driver (i've used https://github.com/goodtft/LCD-show)
    * if using the 
2. attach the mouse or configure it via bluetooth 

# quickstart instructions

these instructions are specific to my setup (Icom IC-705 and Kenwood TH-D74) but since hamlib supports many rigs it could work with other radios as well, the only thing that would change would be the specific device setup.
Also tried it with [kappanhang](https://github.com/nonoo/kappanhang) for remote CAT control to the Icom IC-705

After you installed the LCD TouchScreen configure it to start at boot (using raspi-config)

1. make sure you have python 3.x installed on the raspberry pi.
2. install git and python3 w/ pip 
    + sudo apt-get install git python3-pip swig -y
3. clone the hamlib repository (from master if you are using the th-d74 since it fixes some initialization issues) 
    + git clone https://github.com/Hamlib/Hamlib.git
4. clone this repository 
    + git clone https://github.com/giordyb/doppler_shifter.git
5. install the requirements to build hamlib 
    + sudo apt-get install automake libtool -y
6. cd into the Hamlib directory 
    + cd Hamlib
7. execute ./bootstrap
8. execute ./configure --with-python-binding PYTHON=$(which python3)
9. execute make -j4 && sudo make install
10. refresh the ld library cache
    + sudo ldconfig
11. cd into the doppler_shifter folder 
    + cd ../doppler_shifter
12. install the required libraries 
    + pip3 install -r requirements.txt
13. copy the 99-serial-usb.rules file in /etc/udev/rules.d/ (needed if you use the same radios as me) 
    + sudo cp 99-serial-usb.rules /etc/udev/rules.d/
14. copy the .service files that are relevant to your situation in the systemd folder in /etc/systemd/system/. these are needed to start up the rigctld daemon, your mileage may vary (in the folder you'll find a few examples). These services will start [rigctld](https://www.mankier.com/1/rigctld) daemons needed to control the radios.
    + sudo cp systemd/*.service /etc/systemd/system/
15. reload the systemd daemon 
    + sudo systemctl daemon-reload
16. edit the config/config.json file and adjust the settings. 
    + If you are using the same equiment as me you only need to edit the observer_conf and the timezone which are used to calculate the doopler shift.
    + you can also change the step size
17. test it manually by running the script
    + python3 doppler_shifter.py
18. if everything works then you can add and enable the service
    + sudo systemctl enable doppler_shifter
    + sudo systemctl start doppler_shifter
    + sudo cp doppler_shifter.desktop /usr/share/applications/ (this will create an icon in the raspberry pi's menu that you can click on and run the software)

19. if available GPS location and time can be set using the IC-705 GPS (see http://www.w1hkj.com/W3YJ/Pi_IC-705_GPS.pdf)