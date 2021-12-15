import time

import RPi.GPIO as GPIO

class GPIO():
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(5, GPIO.OUT)

    def switchRelayBorad(self, channelNumber):
        if channelNumber==1 or channelNumber==2:
            GPIO.output(5, 1)
        else:
            GPIO.output(5, 0)
        time.sleep(0.5)