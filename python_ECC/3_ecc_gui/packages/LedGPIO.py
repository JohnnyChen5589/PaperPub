import gpiod
import time

class LedGPIO:
    def __init__(self, pin=17):
        self.pin = pin
        self.chip = gpiod.Chip('gpiochip4')
        self.led_line = self.chip.get_line(self.pin)
        self.led_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)

    def turn_on(self):
        self.led_line.set_value(1)

    def turn_off(self):
        self.led_line.set_value(0)

    def release(self):
        self.led_line.release()
