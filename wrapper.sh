#!/bin/bash
#/usr/local/bin/rigctld -t 4533 -m 2042 -r /dev/ttyUSB-d74 &
#sleep 30
# Optionally set PYTHONPATH
sudo systemctl stop rigup
sudo systemctl stop rigdown

export PYTHONPATH=/home/pi/python-th-d74-cat:$PYTHONPATH

/usr/bin/python3 /home/pi/python-th-d74-cat/print-lcd.py "start doppler_shifter?"
/usr/bin/python3 /home/pi/python-th-d74-cat/doppler_shifter.py
