# -------------------------------------------------------------
# statecontroller.py
# Name: Sam Vinson
# Course: BENG 48203 Senior Biological Engineering Design II
# Date: 03/31/2026
# Purpose: take the states from states.py and apply logic
# to all components such as vision, actuator, buttons
# -------------------------------------------------------------
import time
from states import MachineState


class StrawberryMachineController:
    def __init__(self, vision, actuator, buttons):
        self.vision = vision
        self.actuator = actuator
        self.buttons = buttons

        self.state = MachineState.IDLE
        self.last_state_change = time.time()

        #self.target_cut_y = 450
        self.current_cut_y = None
        self.cut_y_history = []
        self.required_stable_frames = 5
        self.cut_y_stability_tol = 6

        self.position_tolerance = 15
        self.actuator_speed = 65

    def set_state(self, new_state):
        if new_state != self.state:
            print(f"STATE: {self.state.name} -> {new_state.name}")
            self.state = new_state
            self.last_state_change = time.time()

    def get_vision_result(self):
        frame, result, key = self.vision.process_and_visualize(
            state_name=self.state.name,
            actuator_status=self.actuator.current_motion,
            #target_cut_y=self.target_cut_y,
        )

        if key == ord("q"):
            raise KeyboardInterrupt

        if frame is None or result is None:
            return None, None

        return frame, result

    def handle_global_inputs(self):
        if self.buttons.consume_stop():
            self.actuator.stop()
            self.set_state(MachineState.STOPPED)

    def update(self):
        self.handle_global_inputs()

        if self.state == MachineState.IDLE:
            self.handle_idle()

        elif self.state == MachineState.SEARCHING:
            self.handle_searching()

        elif self.state == MachineState.POSITIONING:
            self.handle_positioning()

        elif self.state == MachineState.READY_TO_CUT:
            self.handle_ready_to_cut()

        elif self.state == MachineState.CUTTING:
            self.handle_cutting()

        elif self.state == MachineState.RESETTING:
            self.handle_resetting()

        elif self.state == MachineState.STOPPED:
            self.handle_stopped()

        elif self.state == MachineState.ERROR:
            self.handle_error()

    def handle_idle(self):
        self.actuator.stop()
        self.get_vision_result()  # still show GUI while idle

        if self.buttons.consume_start():
            self.set_state(MachineState.SEARCHING)

    def handle_searching(self):
        frame, result = self.get_vision_result()

        if frame is None or result is None:
            self.set_state(MachineState.ERROR)
            return

        cut_y = result.get("cut_y")

        if cut_y is None:
            print("No strawberry / cutline found yet")
            self.cut_y_history.clear()
            return

        self.cut_y_history.append(cut_y)
        
        # Keep only the most recent N frames
        if len(self.cut_y_history) > self.required_stable_frames:
            self.cut_y_history.pop(0)

        print(f"Searching... cut_y={cut_y}, history={self.cut_y_history}")

        # Need enough frames before deciding stability
        if len(self.cut_y_history) < self.required_stable_frames:
            return

        # Check if recent detections are close enough together
        min_y = min(self.cut_y_history)
        max_y = max(self.cut_y_history)

        if (max_y - min_y) <= self.cut_y_stability_tol:
            locked_cut_y = int(sum(self.cut_y_history) / len(self.cut_y_history))
            self.current_cut_y = locked_cut_y

            print(f"Locked stable cut_y = {locked_cut_y}")
            self.cut_y_history.clear()
            self.set_state(MachineState.POSITIONING)
        else:
            print(
                f"cut_y not stable yet "
                f"(spread={max_y - min_y}, tol={self.cut_y_stability_tol})"
            )

    def handle_positioning(self):
        frame, result = self.get_vision_result()

        if frame is None or result is None:
            self.set_state(MachineState.ERROR)
            return

        cut_y = result.get("cut_y")
        if cut_y is None:
            self.actuator.stop()
            self.set_state(MachineState.SEARCHING)
            return

        self.current_cut_y = cut_y
        #fix later
        #error = self.target_cut_y - self.current_cut_y
    '''
        print(f"Position error = {error}")

        if abs(error) <= self.position_tolerance:
            self.actuator.stop()
            self.set_state(MachineState.READY_TO_CUT)
            return

        # flip these if motion direction is backwards
        if error > 0:
            self.actuator.extend(self.actuator_speed)
        else:
            self.actuator.retract(self.actuator_speed)
    '''

    def handle_ready_to_cut(self):
        self.actuator.stop()
        self.get_vision_result()
        print("Position reached. Ready to cut.")
        time.sleep(0.3)
        self.set_state(MachineState.CUTTING)

    def handle_cutting(self):
        self.get_vision_result()
        print("Perform cut action here")
        time.sleep(0.5)
        self.set_state(MachineState.RESETTING)

    def handle_resetting(self):
        self.get_vision_result()
        print("Resetting system")
        self.actuator.retract(60)
        time.sleep(1.0)
        self.actuator.stop()
        self.set_state(MachineState.IDLE)

    def handle_stopped(self):
        self.actuator.stop()
        self.get_vision_result()
        print("Machine stopped. Press start to resume.")
        if self.buttons.consume_start():
            self.set_state(MachineState.SEARCHING)

    def handle_error(self):
        self.actuator.stop()
        self.get_vision_result()
        print("System error. Press start to retry.")
        if self.buttons.consume_start():
            self.set_state(MachineState.IDLE)