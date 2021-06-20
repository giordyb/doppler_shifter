#%%
import datetime
import ephem
import math
import os
import sys
import time
import urllib2

observer = ephem.Observer()
observer.long = "9.2083"
observer.lat = "45.5208"
observer.date = datetime.datetime.now()

tles = urllib2.urlopen(
    "http://www.amsat.org/amsat/ftp/keps/current/nasabare.txt"
).readlines()
tles = [item.strip() for item in tles]
tles = [(tles[i], tles[i + 1], tles[i + 2]) for i in xrange(0, len(tles) - 2, 3)]

for tle in tles:

    try:
        sat = ephem.readtle(tle[0], tle[1], tle[2])
        rt, ra, tt, ta, st, sa = observer.next_pass(sat)

        if rt is not None and st is not None:
            # observer.date = rt
            sat.compute(observer)

            print tle[0]
            print "rise time: ", ephem.localtime(rt)
            print "set time: ", ephem.localtime(st)
            print
    except ValueError as e:
        print e
# %%
