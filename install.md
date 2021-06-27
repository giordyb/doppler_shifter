
# hardware needed

1. a raspberry pi (tested on a 3b and 4b) with an sd card and raspbian installed
2. a rotary encoder (KY-040)
3. a 20x4 i2c lcd display (I have used this one https://www.amazon.it/gp/product/B0859YY2NZ/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1)
4. some wires to hook up the rotary encoder and the lcd display

# hardware setup
1. connect the 20x4 i2c lcd using this guide: https://www.circuitbasics.com/raspberry-pi-i2c-lcd-set-up-and-programming/
2. connect the rotary encoder https://thepihut.com/blogs/raspberry-pi-tutorials/how-to-use-a-rotary-encoder-with-the-raspberry-pi
3. edit the config.json file to specify the gpio pins that you have used to connect the rotary encoder
4. run "sudo raspi-config" and enable both SPI and I2C from "Interface Options"

# quickstart instructions

these instructions are specific to my setup (Icom IC-705 and Kenwood TH-D74) but since hamlib supports many rigs it could work with other radios as well, the only thing that would change would be the specific device setup


1. make sure you have python 3.x installed on the raspberry pi
2. install git and python3 w/ pip 
    + sudo apt-get install git python3-pip -y
3. clone the hamlib repository (from master if you are using the th-d74 since it fixes some initialization issues) 
    + git clone https://github.com/Hamlib/Hamlib.git
4. clone this repository 
    + git clone https://github.com/giordyb/doppler_shifter.git
4. install the requirements to build hamlib 
    + sudo apt-get install automake libtool -y
5. cd into the Hamlib directory 
    + cd Hamlib
6. execute ./bootstrap
7. execute ./configure
8. execute make -j4 && sudo make install
9. refresh the ld library cache
    + sudo ldconfig
10. cd into the doppler_shifter folder 
    + cd ../doppler_shifter
11. install the required libraries 
    + pip3 install -r requirements.txt
12. copy the 99-serial-usb.rules file in /etc/udev/rules.d/ 
    + sudo cp 99-serial-usb.rules /etc/udev/rules.d/
13. copy the .service files in the systemd folder in /etc/systemd/system/ 
    + sudo cp *.service /etc/systemd/system/
14. reload the systemd daemon 
    + sudo systemctl daemon-reload
15. test it manually by running the script
    + python3 doppler_shifter.py
16. if everything works then you can add the wrapper script to crontab
    + crontab -e
    + @reboot /home/pi/doppler_shifter/wrapper.sh