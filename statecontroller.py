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

        actuator.setInitPos()

        #self.target_cut_y = 450
        self.current_cut_y = None
        self.cut_y_history = []
        self.required_stable_frames = 8
        self.cut_y_stability_tol = 8

        self.first_detection_time = None
        self.min_settle_time = 0.35

        self.positioning_started = False
        self.time_position_found = time.time()

    def time_in_state(self):
        return time.time() - self.last_state_change
    
    def set_state(self, new_state):
        if new_state != self.state:
            print(f"STATE: {self.state.name} -> {new_state.name}")
            self.state = new_state
            self.last_state_change = time.time()
        if new_state!= MachineState.POSITIONING:
            self.positioning_started= False
        # Power logic
        if new_state in [
            MachineState.SEARCHING,
            MachineState.POSITIONING,
            MachineState.READY_TO_CUT,
            MachineState.CUTTING,
        ]:
            self.buttons.power_on()
        else:
            self.buttons.power_off()

    def get_vision_result(self):
        frame, result, key = self.vision.process_and_visualize(
            state_name=self.state.name,
            actuator_status=self.actuator.current_motion,
        )

        if key == ord("q") or key == 27:
            raise KeyboardInterrupt
        elif key == ord("1"):
            print("starting :)")
            self.buttons.keyboardStart()
        elif key == ord("2"):
            print("stopping :)")
            self.buttons.keyboardStop()
        elif key == ord("h"):
            print("---------------Help Menu---------------")
            print("q or ESC - Terminate the program")
            print("1 - Start system")
            print("2 - Stop system")
            print("h - Show help menu")
            print("m - Toggle red & green masks on/off")
            print("---------------------------------------")
        

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

        cut_y_raw = result.get("cut_y_raw")
        berry_box = result.get("berry_box")

        if cut_y_raw is None or berry_box is None:
            self.cut_y_history.clear()
            self.first_detection_time = None
            return

        bx, by, bw, bh = berry_box

        # Optional: reject tiny berries that are just entering view
        if bh < 65:
            self.cut_y_history.clear()
            self.first_detection_time = None
            print(f"Berry detected but not settled yet (height={bh})")
            return

        if self.first_detection_time is None:
            self.first_detection_time = time.time()

        self.cut_y_history.append(cut_y_raw)

        if len(self.cut_y_history) > self.required_stable_frames:
            self.cut_y_history.pop(0)

        print(f"Searching... raw cut_y={cut_y_raw}, history={self.cut_y_history}")

        if len(self.cut_y_history) < self.required_stable_frames:
            return

        min_y = min(self.cut_y_history)
        max_y = max(self.cut_y_history)
        spread = max_y - min_y
        settle_time = time.time() - self.first_detection_time

        if settle_time < self.min_settle_time:
            print(f"Waiting for settle time... {settle_time:.2f}/{self.min_settle_time:.2f}s")
            return

        if spread <= self.cut_y_stability_tol:
            locked_cut_y = int(sum(self.cut_y_history) / len(self.cut_y_history))
            self.current_cut_y = locked_cut_y

            print(f"Locked stable cut_y = {locked_cut_y}")
            self.cut_y_history.clear()
            self.first_detection_time = None
            self.time_position_found = time.time()
            self.set_state(MachineState.POSITIONING)
        else:
            print(f"cut_y not stable yet (spread={spread}, tol={self.cut_y_stability_tol})")

    def handle_positioning(self):
        #frame, result = self.get_vision_result()
        self.get_vision_result()

        #if frame is None or result is None:
        #    self.set_state(MachineState.ERROR)
        #    return

        if self.current_cut_y is None:
            self.set_state(MachineState.ERROR)
            return

        #moves actuator using moveActuator function
        #if self.actuator.moveActuator(self.current_cut_y, self.buttons):
        #    self.set_state(MachineState.READY_TO_CUT)
        #else: 
        #    self.set_state(MachineState.ERROR)

        if not self.positioning_started:
            result = self.actuator.start_move_to_cut_y(self.current_cut_y, duty=70)

            if result is True:
                self.positioning_started = False
                self.set_state(MachineState.READY_TO_CUT)
                return
            elif result is False:
                self.positioning_started = False
                self.set_state(MachineState.ERROR)
                return
            else:
                self.positioning_started = True
                return

        result = self.actuator.update_motion(self.buttons)

        if result is True:
            self.positioning_started = False
            self.set_state(MachineState.READY_TO_CUT)
        elif result is False:
            self.positioning_started = False
            self.set_state(MachineState.STOPPED)


    def handle_ready_to_cut(self):
        self.actuator.stop()
        self.get_vision_result()

        #print("Position reached. Ready to cut.")

        if time.time() - self.time_position_found >= 32:
            self.set_state(MachineState.CUTTING)

    def handle_cutting(self):
        self.get_vision_result()
        #print("Perform cut action here")
        if self.time_in_state() >= 6:
            self.set_state(MachineState.RESETTING)

    def handle_resetting(self):
        self.get_vision_result()
        #print("Resetting system")
        if self.time_in_state() < 1.0:
            #self.actuator.retract(60)
            pass
        else:
            self.actuator.stop()
            self.set_state(MachineState.SEARCHING)

    def handle_stopped(self):
        self.actuator.stop()
        self.get_vision_result()
        #print("Machine stopped. Press start to resume.")
        if self.buttons.consume_start():
            self.set_state(MachineState.SEARCHING)

    def handle_error(self):
        self.actuator.stop()
        self.get_vision_result()
        #print("System error. Press start to retry.")
        if self.buttons.consume_start():
            self.set_state(MachineState.IDLE)