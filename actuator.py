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

# A is slope/weight of regression (mm/pix) B is the y-intercept / bias (mm)
REGRESSIONA=-0.15344313828
REGRESSIONB=165.772356659

#velocity at 70 duty cycle (mm/s)
ACTUATORVELOCITY = 3.76356164383562
# won't move if the difference is this small
ACTUATORTOLERANCE =1.5

#cup height plus velcro
ACTUATORLOWEST = 90
#experimentally determined.... both in mm
LOWESTCUTHEIGHT = 108

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
        # let this position be in mm
        self.current_position = 0

        self.motion_active = False
        self.motion_target = None
        self.motion_unsafetarget = None
        self.motion_direction = None
        self.motion_start_time = None
        self.motion_duration = 0.0
        self.motion_start_position = self.current_position

    def setInitPos(self, duty = 100):
        print("Calibrating actuator for 15 seconds....")
        self.retract(duty)
        time.sleep(15)
        self.stop()
        self.current_position = ACTUATORLOWEST

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
  
    def start_move_to_cut_y(self, cut_y, duty=70):
        strawberryHeight = REGRESSIONA * cut_y + REGRESSIONB
        sterawberryHeight0 = strawberryHeight

        if strawberryHeight < LOWESTCUTHEIGHT: 
            strawberryHeight = LOWESTCUTHEIGHT

        if strawberryHeight < 0:
            print("Computed target height invalid")
            return False

        positionDifference = strawberryHeight - self.current_position

        if abs(positionDifference) < ACTUATORTOLERANCE:
            print(f"Within tolerance ({ACTUATORTOLERANCE} mm), ready.")
            print(f"Strawberry Height 0 ({sterawberryHeight0})")
            self.motion_active = False
            return True

        self.motion_unsafetarget = sterawberryHeight0
        self.motion_target = strawberryHeight
        self.motion_start_position = self.current_position
        self.motion_duration = abs(positionDifference) / ACTUATORVELOCITY
        self.motion_start_time = time.time()

        if positionDifference > 0:
            self.extend(duty=duty)
            self.motion_direction = "extend"
        else:
            self.retract(duty=duty)
            self.motion_direction = "retract"

        self.motion_active = True

        print(f"Starting move:")
        print(f"  cut_y = {cut_y}")
        print(f"  current = {self.current_position:.2f} mm")
        print(f"  potentially unsafe target = {self.motion_unsafetarget:.2f} mm")
        print(f"  target  = {self.motion_target:.2f} mm")
        print(f"  delta   = {positionDifference:.2f} mm")
        print(f"  time    = {self.motion_duration:.2f} s")
        print(f"  dir     = {self.motion_direction}")

        return None

    def update_motion(self, buttons=None):
        if not self.motion_active:
            return True

        if buttons is not None and buttons.consume_stop():
            print("Actuator move interrupted by stop request")
            self.stop_motion()
            return False

        elapsed = time.time() - self.motion_start_time

        if elapsed >= self.motion_duration:
            self.stop()
            self.current_position = self.motion_target
            self.motion_active = False
            print(f"Move complete. Current position = {self.current_position:.2f} mm")
            return True

        return None

    def stop_motion(self):
        self.stop()
        self.motion_active = False
        self.motion_target = None
        self.motion_direction = None
        self.motion_start_time = None
        self.motion_duration = 0.0

    def cleanup(self):
        try:
            self.stop()
            self.rpwm.disable()
            self.lpwm.disable()
            self.rpwm.unexport()
            self.lpwm.unexport()
        finally:
            GPIO.cleanup()