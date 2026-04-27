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
from actuator import ACTUATORVELOCITY, REGRESSIONA, REGRESSIONB, LOWESTCUTHEIGHT


class StrawberryMachineController:
    def __init__(self, vision, actuator, buttons):
        self.vision = vision
        self.actuator = actuator
        self.buttons = buttons

        self.state = MachineState.IDLE
        self.last_state_change = time.time()

        actuator.setInitPos()

        #new changes
        self.cut_queue = []
        self.active_job = None
        self.next_job_id = 1

        self.conveyor_delay = 32.0
        self.cut_duration = 5.0
        self.reset_duration = 1.0
        self.pre_position_margin = 1.0
        self.last_accepted_berry_time = 0.0
        self.new_berry_cooldown = 1.0

        #duplicate prevention latch
        self.berry_locked_in_view = False
        self.release_height_threshold = 45


        #self.target_cut_y = 450
        #self.current_cut_y = None
        self.cut_y_history = []
        self.required_stable_frames = 8
        self.cut_y_stability_tol = 8

        self.first_detection_time = None
        self.min_settle_time = 0.35

        #self.positioning_started = False
        self.time_position_found = time.time()

        self.queue_overlay = ""

    def time_in_state(self):
        return time.time() - self.last_state_change
    
    def set_state(self, new_state):
        if new_state != self.state:
            print(f"STATE: {self.state.name} -> {new_state.name}")
            self.state = new_state
            self.last_state_change = time.time()

        if new_state == MachineState.RUNNING:
            self.buttons.power_on()
        else:
            self.buttons.power_off()

    def get_vision_result(self):
        frame, result, key = self.vision.process_and_visualize(
            state_name=self.state.name,
            actuator_status=self.actuator.current_motion,
            queue_lines=self.build_queue_overlay(),
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

        elif self.state == MachineState.RUNNING:
            self.handle_running()

        elif self.state == MachineState.STOPPED:
            self.handle_stopped()

        elif self.state == MachineState.ERROR:
            self.handle_error()

    def handle_idle(self):
        self.actuator.stop()
        self.get_vision_result()  # still show GUI while idle

        if self.buttons.consume_start():
            self.cut_queue.clear()
            self.active_job = None
            self.cut_y_history.clear()
            self.first_detection_time = None
            self.last_accepted_berry_time = 0.0
            self.set_state(MachineState.RUNNING)

    def handle_running(self):
        frame, result = self.get_vision_result()

        if frame is None or result is None:
            self.set_state(MachineState.ERROR)
            return

        self.update_detection_queue(result)
        self.update_active_job()

        # optional debug
        if self.active_job is not None:
            pass
            #print(f"ACTIVE JOB: {self.active_job['id']} state={self.active_job['stage']}")
        if self.cut_queue:
            pass
            #print(f"QUEUE LEN: {len(self.cut_queue)}")

    def update_detection_queue(self, result):
        cut_y_raw = result.get("cut_y_raw")
        berry_box = result.get("berry_box")

        # -------------------------------------------------
        # No berry visible -> fully reset tracking and latch
        # -------------------------------------------------
        if berry_box is None or cut_y_raw is None:
            self.cut_y_history.clear()
            self.first_detection_time = None
            self.berry_locked_in_view = False
            return

        bx, by, bw, bh = berry_box

        # -------------------------------------------------
        # If the currently latched berry has mostly left view,
        # release the latch so the next berry can be queued
        # -------------------------------------------------
        if self.berry_locked_in_view:
            if bh <= self.release_height_threshold:
                self.berry_locked_in_view = False
                self.cut_y_history.clear()
                self.first_detection_time = None
            return

        # -------------------------------------------------
        # Reject berry still entering / too small
        # -------------------------------------------------
        if bh < 65:
            self.cut_y_history.clear()
            self.first_detection_time = None
            return

        # -------------------------------------------------
        # Stability logic
        # -------------------------------------------------
        if self.first_detection_time is None:
            self.first_detection_time = time.time()

        self.cut_y_history.append(cut_y_raw)

        if len(self.cut_y_history) > self.required_stable_frames:
            self.cut_y_history.pop(0)

        if len(self.cut_y_history) < self.required_stable_frames:
            return

        min_y = min(self.cut_y_history)
        max_y = max(self.cut_y_history)
        spread = max_y - min_y
        settle_time = time.time() - self.first_detection_time

        if settle_time < self.min_settle_time:
            return

        if spread > self.cut_y_stability_tol:
            return

        now = time.time()

        # optional extra cooldown safety
        if now - self.last_accepted_berry_time < self.new_berry_cooldown:
            return

        locked_cut_y = int(sum(self.cut_y_history) / len(self.cut_y_history))

        job = {
            "id": self.next_job_id,
            "cut_y": locked_cut_y,
            "queued_at": now,
            "arrival_time": now + self.conveyor_delay,
            "stage": "queued",
            "positioning_started": False,
            "cut_start": None,
            "reset_start": None,
        }

        self.cut_queue.append(job)
        self.next_job_id += 1
        self.last_accepted_berry_time = now

        # VERY IMPORTANT: latch this visible berry so it cannot be queued again
        self.berry_locked_in_view = True

        print(f"Queued berry #{job['id']} with cut_y={locked_cut_y}, arrival={job['arrival_time']:.2f}")

        self.cut_y_history.clear()
        self.first_detection_time = None

    
    def estimate_move_time(self, cut_y):
        strawberryHeight = REGRESSIONA * cut_y + REGRESSIONB
        if strawberryHeight < LOWESTCUTHEIGHT:
            strawberryHeight = LOWESTCUTHEIGHT

        distance = abs(strawberryHeight - self.actuator.current_position)
        base_time = distance / ACTUATORVELOCITY
        val = base_time * 1.15 + 0.20
        return val
    
    def update_active_job(self):
        now = time.time()

        # pick next job if none active
        if self.active_job is None and self.cut_queue:
            self.active_job = self.cut_queue.pop(0)
            print(f"Activated berry #{self.active_job['id']}")

        if self.active_job is None:
            return

        job = self.active_job

        # -------------------------
        # STAGE 1: queued -> positioning
        # -------------------------
        if job["stage"] == "queued":
            move_time = self.estimate_move_time(job["cut_y"])
            start_move_time = job["arrival_time"] - move_time - self.pre_position_margin

            if now >= start_move_time:
                result = self.actuator.start_move_to_cut_y(job["cut_y"], duty=70)

                if result is True:
                    job["stage"] = "armed"
                    print(f"Berry #{job['id']} already in position")
                elif result is False:
                    self.set_state(MachineState.ERROR)
                    return
                else:
                    job["stage"] = "positioning"
                    print(f"Berry #{job['id']} started positioning")

        # -------------------------
        # STAGE 2: positioning
        # -------------------------
        elif job["stage"] == "positioning":
            result = self.actuator.update_motion(self.buttons)

            if result is True:
                job["stage"] = "armed"
                print(f"Berry #{job['id']} positioned and armed")
            elif result is False:
                self.set_state(MachineState.STOPPED)
                return

        # -------------------------
        # STAGE 3: armed -> cutting
        # -------------------------
        elif job["stage"] == "armed":
            if now >= job["arrival_time"]:
                job["cut_start"] = now
                job["stage"] = "cutting"
                print(f"Berry #{job['id']} cutting")

        # -------------------------
        # STAGE 4: cutting -> resetting
        # -------------------------
        elif job["stage"] == "cutting":
            if now - job["cut_start"] >= self.cut_duration:
                job["reset_start"] = now
                job["stage"] = "resetting"
                print(f"Berry #{job['id']} resetting")

        # -------------------------
        # STAGE 5: resetting -> done
        # -------------------------
        elif job["stage"] == "resetting":
            if now - job["reset_start"] >= self.reset_duration:
                print(f"Berry #{job['id']} complete")
                self.active_job = None

    
    '''
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
    '''
    def handle_stopped(self):
        self.actuator.stop()
        self.get_vision_result()
        #print("Machine stopped. Press start to resume.")
        if self.buttons.consume_start():
            self.cut_queue.clear()
            self.active_job = None
            self.cut_y_history.clear()
            self.first_detection_time = None
            self.set_state(MachineState.RUNNING)


    def handle_error(self):
        self.actuator.stop()
        self.get_vision_result()
        #print("System error. Press start to retry.")
        if self.buttons.consume_start():
            self.cut_queue.clear()
            self.active_job = None
            self.cut_y_history.clear()
            self.first_detection_time = None
            self.set_state(MachineState.IDLE)

    def log_event(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def build_queue_overlay(self):
        lines = []

        # line 1: active berry
        if self.active_job is not None:
            lines.append(
                f"ACTIVE: #{self.active_job['id']} | {self.active_job['stage']} | cut_y={self.active_job['cut_y']}"
            )
        else:
            lines.append("ACTIVE: none")

        # line 2: queued berries
        if self.cut_queue:
            queued_ids = [f"#{job['id']}" for job in self.cut_queue[:5]]
            queue_text = " ".join(queued_ids)

            if len(self.cut_queue) > 5:
                queue_text += " ..."

            lines.append(f"QUEUE ({len(self.cut_queue)}): {queue_text}")
        else:
            lines.append("QUEUE (0): empty")

        return lines