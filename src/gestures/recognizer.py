import time
from collections import deque

class GestureRecognizer:
    def __init__(self, swipe_threshold=0.15, cooldown_time=1.5):
        """
        Initializes the GestureRecognizer.
        
        Args:
            swipe_threshold: Minimum horizontal movement (normalized) to register a swipe.
            cooldown_time: Seconds to wait before allowing another dynamic gesture.
        """
        self.swipe_threshold = swipe_threshold
        self.cooldown_time = cooldown_time
        
        self.last_gesture_time = 0
        self.current_gesture = "None"
        
        # History for dynamic gestures (store X coordinates of wrist)
        self.wrist_history = deque(maxlen=10)
        
        # Landmark indices for finger tips and their corresponding lower joints (PIP)
        self.TIP_IDS = [4, 8, 12, 16, 20]
        self.PIP_IDS = [2, 6, 10, 14, 18]

    def _get_fingers_up(self, hand_landmarks):
        """
        Determines which fingers are raised by comparing tip coordinates to other joints.
        """
        fingers = []
        
        # 1. Thumb: Check distance of Thumb TIP (4) to Pinky MCP (17) 
        # compared to Thumb MCP (2) to Pinky MCP (17). If tip is further away, it's extended.
        tip_pinky_dist = ((hand_landmarks[4].x - hand_landmarks[17].x)**2 + (hand_landmarks[4].y - hand_landmarks[17].y)**2)
        mcp_pinky_dist = ((hand_landmarks[2].x - hand_landmarks[17].x)**2 + (hand_landmarks[2].y - hand_landmarks[17].y)**2)
        fingers.append(1 if tip_pinky_dist > mcp_pinky_dist else 0)

        # 2. Four Fingers (Index, Middle, Ring, Pinky)
        wrist = hand_landmarks[0]
        for id in range(1, 5):
            tip = hand_landmarks[self.TIP_IDS[id]]
            pip = hand_landmarks[self.PIP_IDS[id]]
            
            # Use distance from the wrist to determine if a finger is extended (rotation invariant)
            dist_tip_wrist = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)
            dist_pip_wrist = ((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2)
            
            if dist_tip_wrist > dist_pip_wrist:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers

    def recognize(self, hand_landmarks):
        """
        Takes the detected hand landmarks, updates state, and returns the recognized gesture.
        """
        if not hand_landmarks:
            self.wrist_history.clear()
            return self.current_gesture
            
        # Get the first hand's landmarks
        landmarks = hand_landmarks[0]
        
        # Track wrist X position for swipes
        wrist_x = landmarks[0].x
        self.wrist_history.append(wrist_x)
        
        # Check cooldown
        if time.time() - self.last_gesture_time < self.cooldown_time:
            return self.current_gesture
            
        fingers = self._get_fingers_up(landmarks)
        total_fingers = sum(fingers)
        
        # Static Gestures
        detected_gesture = "None"
        
        if total_fingers <= 1:
            detected_gesture = "CLOSED_FIST"
        elif total_fingers >= 4:
            detected_gesture = "OPEN_PALM"
        elif fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            # Index is up, all other fingers (except maybe thumb) are down
            detected_gesture = "INDEX_POINTING"
        elif fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
            # Index and Middle are up
            detected_gesture = "TWO_FINGERS"
            
        # Dynamic Gestures (Swipes)
        # Allow swipe if hand is mostly open (e.g. at least 3 fingers up) to be more forgiving
        if total_fingers >= 3 and len(self.wrist_history) > 3:
            max_x = max(self.wrist_history)
            min_x = min(self.wrist_history)
            
            # If the total horizontal movement in our recent history exceeds the threshold
            if (max_x - min_x) > self.swipe_threshold:
                history_list = list(self.wrist_history)
                max_idx = history_list.index(max_x)
                min_idx = history_list.index(min_x)
                
                # If the minimum X happened before the maximum X, the hand moved Right
                if max_idx > min_idx:
                    detected_gesture = "SWIPE_RIGHT"
                else:
                    detected_gesture = "SWIPE_LEFT"
                    
                self.last_gesture_time = time.time()
                self.wrist_history.clear()

        # Update and return
        self.current_gesture = detected_gesture
        return self.current_gesture
