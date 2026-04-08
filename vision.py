# -------------------------------------------------------------
# vision.py
# Name: Sam Vinson
# Course: BENG 48203 Senior Biological Engineering Design II
# Date: 03/31/2026
# Purpose: create openCV windows and also determine cutting line
# -------------------------------------------------------------
import cv2
import time
import numpy as np


class VisionSystem:
    def __init__(
        self,
        device="/dev/video0",
        capture_width=1280,
        capture_height=720,
        capture_fps=30,
        show_masks=True,
        enable_gui=True,
    ):
        self.device = device
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.capture_fps = capture_fps

        self.show_masks = show_masks
        self.enable_gui = enable_gui

        self.prev_time = time.time()
        self.last_fps = 0.0

        self.filtered_cut_y = None

        self.cap = cv2.VideoCapture(self.build_pipeline(), cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("Error: failed to open camera.")

    def build_pipeline(self):
        return (
            f"v4l2src device={self.device} ! "
            f"image/jpeg, width={self.capture_width}, height={self.capture_height}, framerate={self.capture_fps}/1 ! "
            f"jpegdec ! "
            f"nvvidconv ! "
            f"video/x-raw, format=BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=BGR ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )

    def largest_contour(self, mask, min_area=100):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best = None
        best_area = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area and area > best_area:
                best = cnt
                best_area = area

        return best

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def analyze(self, frame):
        H, W = frame.shape[:2]

        rx1 = int(W * 0.40)
        ry1 = int(H * 0.30)
        rx2 = int(W * 0.72)
        ry2 = int(H * 0.78)

        roi = frame[ry1:ry2, rx1:rx2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 90, 50], dtype=np.uint8)
        upper_red1 = np.array([12, 255, 255], dtype=np.uint8)
        lower_red2 = np.array([165, 90, 50], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        lower_green = np.array([35, 40, 40], dtype=np.uint8)
        upper_green = np.array([95, 255, 255], dtype=np.uint8)
        green_mask_raw = cv2.inRange(hsv, lower_green, upper_green)

        kernel3 = np.ones((3, 3), np.uint8)
        kernel5 = np.ones((5, 5), np.uint8)
        kernel7 = np.ones((7,7), np.uint8)

        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel3)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel5)

        green_mask_raw = cv2.morphologyEx(green_mask_raw, cv2.MORPH_OPEN, kernel5)
        green_mask_raw = cv2.morphologyEx(green_mask_raw, cv2.MORPH_CLOSE, kernel7)

        berry_contour = self.largest_contour(red_mask, min_area=150)

        berry_box = None
        cut_y = None
        green_near_berry = np.zeros_like(green_mask_raw)

        if berry_contour is not None:
            x, y, w, h = cv2.boundingRect(berry_contour)
            berry_box = (rx1 + x, ry1 + y, w, h)

            berry_left = x
            berry_right = x + w

            # inside analyze(), after berry box is found
            green_near_berry = np.zeros_like(green_mask_raw)

            pad_x = 40
            pad_y_top = 80
            pad_y_bottom = 20

            gx1 = max(0, berry_left - pad_x)
            gx2 = min(green_mask_raw.shape[1], berry_right + pad_x)
            gy1 = max(0, y - pad_y_top)
            gy2 = min(green_mask_raw.shape[0], y + pad_y_bottom)

            green_near_berry[gy1:gy2, gx1:gx2] = green_mask_raw[gy1:gy2, gx1:gx2]

            green_contour = self.largest_contour(green_near_berry, min_area=80)

            if green_contour is not None:
                gx, gy, gw, gh = cv2.boundingRect(green_contour)
                cut_y_roi = gy + gh + 42
                cut_y = ry1 + cut_y_roi
            else:
                alpha = 0.25
                cut_y_roi = int(y + alpha * h)
                cut_y = ry1 + cut_y_roi

            # smooth cut_y
            if cut_y is not None:
                if self.filtered_cut_y is None:
                    self.filtered_cut_y = cut_y
                else:
                    beta = 0.2
                    new_cut = int(beta * cut_y + (1 - beta) * self.filtered_cut_y)

                    if abs(new_cut - self.filtered_cut_y) < 4:
                        new_cut = self.filtered_cut_y

                    max_step = 5
                    delta = new_cut - self.filtered_cut_y
                    delta = max(-max_step, min(max_step, delta))
                    self.filtered_cut_y = self.filtered_cut_y + delta

                cut_y = self.filtered_cut_y

        else:
            berry_box = None
            cut_y = None
            self.filtered_cut_y = None

        return {
            "roi_box": (rx1, ry1, rx2, ry2),
            "berry_box": berry_box,
            "cut_y": cut_y,
            "red_mask": red_mask,
            "green_mask_raw": green_mask_raw,
            "green_mask": green_near_berry,
            "berry_contour": berry_contour,
            "roi_origin": (rx1, ry1),
        }

    def update_fps(self):
        current_time = time.time()
        self.last_fps = 1.0 / (current_time - self.prev_time) if current_time > self.prev_time else 0.0
        self.prev_time = current_time
        return self.last_fps

    def render(self, frame, result, state_name=None, actuator_status=None):
        display_frame = frame.copy()

        rx1, ry1, rx2, ry2 = result["roi_box"]
        cv2.rectangle(display_frame, (rx1, ry1), (rx2, ry2), (0, 255, 0), 2)

        if result["berry_box"] is not None:
            bx, by, bw, bh = result["berry_box"]
            cv2.rectangle(display_frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)

        if result["cut_y"] is not None:
            cut_y = result["cut_y"]
            cv2.line(display_frame, (rx1, cut_y), (rx2, cut_y), (255, 0, 0), 3)
            cv2.putText(
                display_frame,
                f"cut_y={cut_y}",
                (rx1, max(30, cut_y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 0),
                2,
                cv2.LINE_AA,
            )
        '''
        if target_cut_y is not None:
            cv2.line(display_frame, (rx1, target_cut_y), (rx2, target_cut_y), (0, 255, 255), 2)
            cv2.putText(
                display_frame,
                f"target={target_cut_y}",
                (rx1, min(display_frame.shape[0] - 20, target_cut_y + 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
        '''

        fps = self.update_fps()
        cv2.putText(
            display_frame,
            f"FPS: {fps:.1f}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        if state_name is not None:
            cv2.putText(
                display_frame,
                f"STATE: {state_name}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

        if actuator_status is not None:
            cv2.putText(
                display_frame,
                f"ACTUATOR: {actuator_status}",
                (20, 115),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 0),
                2,
                cv2.LINE_AA,
            )

        return display_frame

    def show(self, display_frame, result):
        if not self.enable_gui:
            return

        cv2.imshow("Jetson Vision Pipeline", display_frame)

        if self.show_masks:
            cv2.imshow("red_mask", result["red_mask"])
            cv2.imshow("green_mask", result["green_mask"])

    def handle_keypress(self):
        if not self.enable_gui:
            return None

        key = cv2.waitKey(1) & 0xFF

        if key == ord("m"):
            self.show_masks = not self.show_masks
            if not self.show_masks:
                try:
                    cv2.destroyWindow("red_mask")
                except cv2.error:
                    pass
                try:
                    cv2.destroyWindow("green_mask")
                except cv2.error:
                    pass

        return key

    def close_windows(self):
        if self.enable_gui:
            cv2.destroyAllWindows()

    def release(self):
        if self.cap is not None:
            self.cap.release()
        self.close_windows()

    def process_and_visualize(self, state_name=None, actuator_status=None):
        frame = self.read()
        if frame is None:
            return None, None, None

        result = self.analyze(frame)
        display_frame = self.render(
            frame,
            result,
            state_name=state_name,
            actuator_status=actuator_status,
            #target_cut_y=target_cut_y,
        )
        self.show(display_frame, result)
        key = self.handle_keypress()
        return frame, result, key
    