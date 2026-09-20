import cv2
import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from vision.hand_tracker import HandTracker
from gestures.recognizer import GestureRecognizer
from control.presentation_controller import PresentationController

class VideoThread(QThread):
    # Signals to communicate with the GUI
    change_pixmap_signal = Signal(QImage)
    update_gesture_signal = Signal(str, str, bool, bool) # action_gesture, confirmed_gesture, is_cooldown, waiting_for_release
    
    def __init__(self):
        super().__init__()
        self._run_flag = True
        
        # Initialize Core Components
        self.tracker = HandTracker(max_num_hands=1, min_detection_confidence=0.7)
        self.recognizer = GestureRecognizer(cooldown_time=1.0, stability_frames=5)
        self.controller = PresentationController(smoothing=0.7)
        self.gestures_active = False
        
        self.gesture_mapping = {
            "Next Slide": "THUMBS_UP",
            "Previous Slide": "THUMBS_DOWN",
            "Screenshot": "TWO_FINGERS",
            "Pointer": "INDEX_POINTING"
        }

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        start_time = time.time()
        last_timestamp_ms = -1

        while self._run_flag:
            success, img = cap.read()
            if not success:
                # If we fail to read, just wait a bit and continue
                time.sleep(0.01)
                continue
                
            img = cv2.flip(img, 1)

            timestamp_ms = int((time.time() - start_time) * 1000)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms

            # Process image for hand tracking
            img, results = self.tracker.find_hands(img, timestamp_ms, draw=True)
            
            # Gesture Recognition
            action_gesture = "None"
            is_pointing = False
            
            if results and results.hand_landmarks:
                action_gesture = self.recognizer.recognize(results.hand_landmarks)
                
                # Only execute actions if gestures are active (Timer is running)
                if self.gestures_active:
                    if action_gesture == self.gesture_mapping["Next Slide"]:
                        self.controller.next_slide()
                    elif action_gesture == self.gesture_mapping["Previous Slide"]:
                        self.controller.previous_slide()
                    elif action_gesture == self.gesture_mapping["Screenshot"]:
                        self.controller.take_screenshot()
                        
                    if action_gesture == self.gesture_mapping["Pointer"]:
                        is_pointing = True
                        index_finger_tip = results.hand_landmarks[0][8]
                        self.controller.move_pointer(index_finger_tip.x, index_finger_tip.y)
            else:
                action_gesture = self.recognizer.recognize(None)

            if not is_pointing:
                self.controller.release_pointer()

            # Emit Signals to GUI
            # 1. Video Frame
            self.emit_frame(img)
            
            # 2. Gesture Data
            self.update_gesture_signal.emit(
                action_gesture,
                self.recognizer.confirmed_gesture,
                self.recognizer.is_cooldown,
                self.recognizer.waiting_for_release
            )

            # Control loop rate to prevent maxing out CPU needlessly
            time.sleep(0.01)

        cap.release()

    def emit_frame(self, cv_img):
        """Converts OpenCV BGR frame to QImage and emits it."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        # Create QImage
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.change_pixmap_signal.emit(qt_img)

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()

    # Dynamic Settings Setters
    def set_cooldown(self, seconds):
        self.recognizer.cooldown_time = seconds

    def set_smoothing(self, value):
        self.controller.smoothing = value
        
    def set_gestures_active(self, active):
        self.gestures_active = active

    def update_gesture_mapping(self, action_name, gesture_name):
        self.gesture_mapping[action_name] = gesture_name
