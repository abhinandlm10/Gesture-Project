import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

class HandTracker:
    def __init__(self, model_path='src/vision/hand_landmarker.task', max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.5):
        """
        Initializes the MediaPipe hand tracking module using the new Tasks API.
        This is fully compatible with Python 3.13!
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"MediaPipe model not found at {model_path}")
            
        base_options = python.BaseOptions(model_asset_path=model_path)
        
        # Using Video mode for real-time tracking from webcam
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        
        # Hand Landmark connections mapping (standard mediapipe 21 points)
        self.HAND_CONNECTIONS = [
            (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),        # Index finger
            (5, 9), (9, 10), (10, 11), (11, 12),   # Middle finger
            (9, 13), (13, 14), (14, 15), (15, 16), # Ring finger
            (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky
        ]
        
        self.results = None

    def find_hands(self, img, timestamp_ms, draw=True):
        """
        Processes an image (frame) to detect hands and draw landmarks.
        """
        # Convert BGR (OpenCV format) to RGB (MediaPipe format)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Create a mediapipe Image object
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        
        # Process the image in video mode
        self.results = self.detector.detect_for_video(mp_image, timestamp_ms)

        # If hands were found and drawing is enabled
        if draw and self.results.hand_landmarks:
            for hand_landmarks in self.results.hand_landmarks:
                self._draw_landmarks(img, hand_landmarks)
                
        return img, self.results
        
    def _draw_landmarks(self, img, hand_landmarks):
        """Helper function to manually draw the 21 hand landmarks and connections."""
        h, w, _ = img.shape
        
        # Convert normalized coordinates to pixel coordinates
        points = []
        for landmark in hand_landmarks:
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            points.append((cx, cy))
            
        # Draw connections
        for connection in self.HAND_CONNECTIONS:
            pt1 = points[connection[0]]
            pt2 = points[connection[1]]
            cv2.line(img, pt1, pt2, (0, 255, 0), 2)  # Green lines
            
        # Draw points
        for pt in points:
            cv2.circle(img, pt, 5, (0, 0, 255), cv2.FILLED)  # Red dots
