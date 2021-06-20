#!/bin/bash
#/usr/local/bin/rigctld -t 4533 -m 2042 -r /dev/ttyUSB-d74 &
#sleep 30
# Optionally set PYTHONPATH
sudo systemctl stop rigup
sudo systemctl stop rigdown

export PYTHONPATH=/home/pi/doppler_shifter:$PYTHONPATH

/usr/bin/python3 /home/pi/doppler_shifter/doppler_shifter.py
