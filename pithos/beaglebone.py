# -*- coding: utf-8 -*-
try:
    import Adafruit_BBIO.ADC as adc
    import Adafruit_BBIO.GPIO as gpio
    beaglebone = True
except:
    beaglebone = False

import threading
import time


class Beaglebone():

    def __init__(self, radiologger, player):
        self.volumePot = "AIN5"
        self.stationPot = "AIN3"
        self.radiologger = radiologger
        self.player = player
        self.common = "P8_10"
        self.red = "P8_12"
        self.green = "P8_14"
        self.blue = "P8_16"

        if beaglebone:
            adc.setup()
            self.radioPowerAndVolume()
            gpio.setup(self.common, gpio.OUT)
            gpio.setup(self.red, gpio.OUT)
            gpio.setup(self.green, gpio.OUT)
            gpio.setup(self.blue, gpio.OUT)
            gpio.output(self.common, gpio.LOW)
            gpio.output(self.red, gpio.LOW)
            gpio.output(self.green, gpio.LOW)
            gpio.output(self.blue, gpio.LOW)

    def radioPowerAndVolume(self):
        def getVolumeAndStationValue():
            prevStation = 0
            while True:
                sample = 0
                volReading = 0
                statReading = 0
                while sample < 10:
                    volReading += adc.read(self.volumePot)
                    time.sleep(0.01)
                    statReading += adc.read(self.stationPot)
                    sample += 1
                    time.sleep(0.05)

                volReading = volReading / 10.0
                statReading = int(statReading * 100)

                station = statReading

                if station != prevStation:
                    # print prevStation, station
                    if self.have_stations:
                        print 'True'
                    prevStation = station

                volume = volReading
                volString = "%.2f" % round(volume, 2)

                previousVolume = self.player.get_property('volume')
                prevVolString = "%.2f" % round(previousVolume, 2)

                if volString != prevVolString:
                    # print previousVolume, volume
                    self.player.set_property('volume', volume)

        thread = threading.Thread(target=getVolumeAndStationValue, args=())
        thread.start()

    def redOn(self):
        if beaglebone:
            gpio.output(self.red, gpio.HIGH)

    def redOff(self):
        if beaglebone:
            gpio.output(self.red, gpio.LOW)

    def greenOn(self):
        if beaglebone:
            gpio.output(self.green, gpio.HIGH)

    def greenOff(self):
        if beaglebone:
            gpio.output(self.green, gpio.LOW)

    def blueOn(self):
        if beaglebone:
            gpio.output(self.blue, gpio.HIGH)

    def blueOff(self):
        if beaglebone:
            gpio.output(self.blue, gpio.LOW)