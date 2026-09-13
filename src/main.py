import cv2
import sys
import time
from vision.hand_tracker import HandTracker
from gestures.recognizer import GestureRecognizer
from control.presentation_controller import PresentationController

def main():
    print("Initializing Smart Gesture Presentation System...")
    
    # Open the default webcam (index 0). Using cv2.CAP_DSHOW on Windows fixes black screen / MSMF errors.
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("Error: Could not access the webcam.")
        sys.exit(1)

    # Initialize the hand tracker with the new Tasks API
    # Max hands = 1 to simplify gestures for Phase 2
    try:
        tracker = HandTracker(max_num_hands=1, min_detection_confidence=0.7)
    except Exception as e:
        print(f"Error initializing hand tracker: {e}")
        sys.exit(1)
        
    # Initialize our gesture recognizer
    recognizer = GestureRecognizer(swipe_threshold=0.15, cooldown_time=1.5)
    
    # Initialize our presentation controller for Phase 3
    controller = PresentationController()

    print("Webcam started successfully.")
    print("--> Press 'q' or 'ESC' to exit.")

    start_time = time.time()
    last_timestamp_ms = -1

    while True:
        # Read a frame from the webcam
        success, img = cap.read()
        if not success:
            print("Warning: Failed to read frame from webcam.")
            break
            
        # Flip the image horizontally so it acts like a mirror
        img = cv2.flip(img, 1)

        # Calculate current timestamp in milliseconds for the video stream
        timestamp_ms = int((time.time() - start_time) * 1000)
        
        # Ensure timestamp is strictly monotonically increasing
        if timestamp_ms <= last_timestamp_ms:
            timestamp_ms = last_timestamp_ms + 1
        last_timestamp_ms = timestamp_ms

        # Process the image to find hands
        img, results = tracker.find_hands(img, timestamp_ms, draw=True)
        
        # Gesture Recognition
        gesture = "None"
        if results and results.hand_landmarks:
            gesture = recognizer.recognize(results.hand_landmarks)
            
            # Map gestures to controller actions
            if gesture == "SWIPE_RIGHT":
                controller.next_slide()
            elif gesture == "SWIPE_LEFT":
                controller.previous_slide()
            elif gesture == "INDEX_POINTING":
                # Get the index finger tip (landmark ID 8)
                index_finger_tip = results.hand_landmarks[0][8]
                # Pass normalized coordinates to the controller
                controller.move_pointer(index_finger_tip.x, index_finger_tip.y)
        else:
            # Pass None so the recognizer can clear its history if the hand leaves the frame
            gesture = recognizer.recognize(None)

        # Draw the detected gesture on the screen (Debug Overlay)
        cv2.putText(img, f'Gesture: {gesture}', (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA)
                    
        # Draw cooldown status if we recently did a dynamic gesture
        time_since_gesture = time.time() - recognizer.last_gesture_time
        if time_since_gesture < recognizer.cooldown_time and gesture in ["SWIPE_LEFT", "SWIPE_RIGHT"]:
            cv2.putText(img, 'COOLDOWN...', (20, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

        # Display the processed image in a window
        cv2.imshow("Gesture Presentation System - Phase 3", img)

        # Check for user input (wait 1ms per frame)
        key = cv2.waitKey(1) & 0xFF
        
        # Break loop if 'q' (113) or 'ESC' (27) is pressed
        if key == ord('q') or key == 27:
            print("Exiting...")
            break

    # Clean up and release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
