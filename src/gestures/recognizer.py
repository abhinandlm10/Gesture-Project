import time
from collections import deque

class GestureRecognizer:
    def __init__(self, cooldown_time=1.5, stability_frames=5):
        """
        Initializes the GestureRecognizer.
        
        Args:
            cooldown_time: Seconds to wait before allowing another dynamic gesture.
            stability_frames: Number of consecutive frames an identical gesture must be seen to confirm it.
        """
        self.cooldown_time = cooldown_time
        self.stability_frames = stability_frames
        
        self.last_action_time = 0
        
        # History for temporal confirmation
        self.history = deque(maxlen=self.stability_frames)
        
        # States for external debugging and release mechanic
        self.raw_gesture = "None"
        self.confirmed_gesture = "None"
        self.locked_gesture = "None"
        self.is_cooldown = False
        self.waiting_for_release = False
        
        self.TIP_IDS = [4, 8, 12, 16, 20]
        self.PIP_IDS = [2, 6, 10, 14, 18]

    def _get_fingers_up(self, hand_landmarks):
        """Determines which fingers are raised by comparing distances."""
        fingers = []
        wrist = hand_landmarks[0]
        
        # Thumb: compare tip to wrist vs mcp to wrist
        tip_pinky_dist = ((hand_landmarks[4].x - hand_landmarks[17].x)**2 + (hand_landmarks[4].y - hand_landmarks[17].y)**2)
        mcp_pinky_dist = ((hand_landmarks[2].x - hand_landmarks[17].x)**2 + (hand_landmarks[2].y - hand_landmarks[17].y)**2)
        fingers.append(1 if tip_pinky_dist > mcp_pinky_dist else 0)

        # Other fingers
        for id in range(1, 5):
            tip = hand_landmarks[self.TIP_IDS[id]]
            pip = hand_landmarks[self.PIP_IDS[id]]
            dist_tip_wrist = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)
            dist_pip_wrist = ((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2)
            fingers.append(1 if dist_tip_wrist > dist_pip_wrist else 0)
                
        return fingers

    def recognize(self, hand_landmarks):
        """Processes landmarks, applies temporal logic, returns triggered gesture."""
        action_gesture = "None"
        
        # Update cooldown state
        self.is_cooldown = (time.time() - self.last_action_time) < self.cooldown_time

        if not hand_landmarks:
            self.history.clear()
            self.raw_gesture = "None"
            self.confirmed_gesture = "None"
            
            # If the hand disappears, we release any locked gestures
            self.locked_gesture = "None"
            self.waiting_for_release = False
            return action_gesture
            
        landmarks = hand_landmarks[0]
        fingers = self._get_fingers_up(landmarks)
        total_fingers = sum(fingers)
        
        # 1. Determine Raw Gesture
        detected_gesture = "None"
        if total_fingers == 0 or (total_fingers == 1 and fingers[0] == 1):
            if fingers[0] == 1:
                # Check orientation based on Y coordinates (smaller Y is higher up)
                # Compare Thumb Tip (4) to Thumb IP (3)
                if landmarks[4].y < landmarks[3].y:
                    detected_gesture = "THUMBS_UP"
                else:
                    detected_gesture = "THUMBS_DOWN"
            else:
                detected_gesture = "CLOSED_FIST"
        elif total_fingers >= 4:
            detected_gesture = "OPEN_PALM"
        elif fingers[1] == 1 and sum(fingers[2:]) == 0:
            detected_gesture = "INDEX_POINTING"
        elif fingers[1] == 1 and fingers[2] == 1 and sum(fingers[3:]) == 0:
            detected_gesture = "TWO_FINGERS"
            
        self.raw_gesture = detected_gesture
        self.history.append(self.raw_gesture)
        
        # 2. Determine Confirmed Gesture (Temporal Confirmation)
        if len(self.history) == self.stability_frames and all(g == self.raw_gesture for g in self.history):
            self.confirmed_gesture = self.raw_gesture
        else:
            self.confirmed_gesture = "None"
            
        # 3. Action Triggering and Release Mechanic
        
        # Free the lock extremely quickly if the physical thumb is dropped (no longer in history)
        if self.locked_gesture != "None" and self.locked_gesture not in self.history:
            self.locked_gesture = "None"
            self.waiting_for_release = False
            
        if self.confirmed_gesture in ["THUMBS_UP", "THUMBS_DOWN"]:
            # If we see the same gesture that is already locked, wait for release
            if self.confirmed_gesture == self.locked_gesture:
                self.waiting_for_release = True
            else:
                self.waiting_for_release = False
                # Trigger action if not in cooldown
                if not self.is_cooldown:
                    action_gesture = self.confirmed_gesture
                    self.last_action_time = time.time()
                    self.is_cooldown = True
                    self.locked_gesture = self.confirmed_gesture
                    self.waiting_for_release = True
        else:
            if self.confirmed_gesture != "None":
                # Continuous gestures like pointing don't lock
                action_gesture = self.confirmed_gesture

        return action_gesture
