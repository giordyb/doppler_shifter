#!/bin/bash
# Optionally set PYTHONPATH
cd /home/pi/doppler_shifter/
#sudo systemctl stop rigup
#sudo systemctl stop rigdown

export PYTHONPATH=/home/pi/doppler_shifter:$PYTHONPATH

/usr/bin/python3 /home/pi/doppler_shifter/doppler_shifter.py
