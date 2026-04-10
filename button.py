# -------------------------------------------------------------
# button.py
# Name: Sam Vinson
# Course: BENG 48203 Senior Biological Engineering Design II
# Date: 03/31/2026
# Purpose: button panel signals
# -------------------------------------------------------------
import Jetson.GPIO as GPIO

class ButtonPanel:
    def __init__(self, start_pin=22, stop_pin=24):
        self.start_pin = start_pin
        self.stop_pin = stop_pin
        
        self.power_pin = 40
        
        self.start_requested = False
        self.stop_requested = False

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.power_pin, GPIO.OUT, initial=GPIO.LOW)  

        GPIO.setup(self.start_pin, GPIO.IN)
        GPIO.setup(self.stop_pin, GPIO.IN)

        GPIO.add_event_detect(self.start_pin, GPIO.FALLING, callback=self._on_start, bouncetime=10)
        GPIO.add_event_detect(self.stop_pin, GPIO.FALLING, callback=self._on_stop, bouncetime=10)

    def _on_start(self, channel):
        self.start_requested = True
        print("Start button pressed")
    
    def _on_stop(self, channel):
        self.start_requested = False
        self.stop_requested = True
        print("Stop button pressed")

    def consume_start(self):
        if self.start_requested:
            self.start_requested = False
            return True
        return False

    def consume_stop(self):
        if self.stop_requested:
            self.stop_requested = False
            return True
        return False

    def status(self):
        # debug
        print(f"Start Requested: {self.start_requested}")
        print(f"Stop Requested: {self.stop_requested}")
        return self.start_requested, self.stop_requested

    def keyboardStart(self):
        self.start_requested = True
        print("Start button pressed via keyboard")

    def keyboardStop(self):
        self.stop_requested = True
        print("Stop button pressed via keyboard")

    def power_on(self):
        GPIO.output(self.power_pin, GPIO.HIGH)

    def power_off(self):
        GPIO.output(self.power_pin, GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()