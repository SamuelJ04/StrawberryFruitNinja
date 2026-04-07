# -------------------------------------------------------------
# actuator.py
# Name: Sam Vinson
# Course: BENG 48203 Senior Biological Engineering Design II
# Date: 03/31/2026
# Purpose: Class for linear actuator and SysfsPWM
# -------------------------------------------------------------
import time
import Jetson.GPIO as GPIO
from pathlib import Path

# Board Pins
# ren and len need to be ON
REN = 19
LEN = 21
RPWM_CHIP = Path("/sys/class/pwm/pwmchip2") # pin 33
LPWM_CHIP = Path("/sys/class/pwm/pwmchip3") # pin 32
PERIOD_NS = 1_000_000 # 1 kHz

#SysfsPWM (over my head and adopted from people who are much smarter than me)
class SysfsPWM:

    def __init__(self, chip_path):
        self.chip = Path(chip_path)
        self.pwm = self.chip / "pwm0"
        self.exported = False

    def export(self):
        if not self.pwm.exists():
            (self.chip / "export").write_text("0")
            time.sleep(0.1)
        self.exported = True

    def unexport(self):
        if self.pwm.exists():
            try:
                self.disable()
            except Exception:
                pass
            (self.chip / "unexport").write_text("0")
            time.sleep(0.1)

    def set_period(self, period_ns):
        (self.pwm / "period").write_text(str(period_ns))

    def set_duty_cycle(self, duty_ns):
        (self.pwm / "duty_cycle").write_text(str(duty_ns))

    def enable(self):
        (self.pwm / "enable").write_text("1")

    def disable(self):
        (self.pwm / "enable").write_text("0")

    def set_duty_percent(self, percent):
        percent = max(0, min(100, percent))
        duty_ns = int(PERIOD_NS * percent / 100.0)
        self.set_duty_cycle(duty_ns)

class LinearActuator:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(REN, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(LEN, GPIO.OUT, initial=GPIO.HIGH)

        #init
        self.rpwm = SysfsPWM(RPWM_CHIP)
        self.lpwm = SysfsPWM(LPWM_CHIP)

        self.rpwm.export()
        self.lpwm.export()

        self.rpwm.set_period(PERIOD_NS)
        self.lpwm.set_period(PERIOD_NS)

        self.rpwm.set_duty_cycle(0)
        self.lpwm.set_duty_cycle(0)

        self.rpwm.enable()
        self.lpwm.enable()

        #set init state for moving
        self.current_motion = "stoppped"

    def extend(self, duty=70):
        self.lpwm.set_duty_percent(0)
        self.rpwm.set_duty_percent(duty)
        self.current_motion = "extending"

    def retract(self, duty=70):
        self.rpwm.set_duty_percent(0)
        self.lpwm.set_duty_percent(duty)
        self.current_motion = "retracting"
    
    def stop(self):
        self.rpwm.set_duty_percent(0)
        self.lpwm.set_duty_percent(0)
        self.current_motion = "stopped"

    def status(self):
        #debug
        print(f"Current motion: {self.current_motion}")

    def cleanup(self):
        try:
            self.stop()
            self.rpwm.disable()
            self.lpwm.disable()
            self.rpwm.unexport()
            self.rpwm.unexport()
        finally:
            GPIO.cleanup()