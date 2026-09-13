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
        
    # Initialize our gesture recognizer with temporal confirmation and a short cooldown
    recognizer = GestureRecognizer(cooldown_time=1.0, stability_frames=5)
    
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
        action_gesture = "None"
        if results and results.hand_landmarks:
            action_gesture = recognizer.recognize(results.hand_landmarks)
            
            # Map gestures to controller actions
            if action_gesture == "THUMBS_UP":
                controller.next_slide()
            elif action_gesture == "THUMBS_DOWN":
                controller.previous_slide()
            elif action_gesture == "INDEX_POINTING":
                # Get the index finger tip (landmark ID 8)
                index_finger_tip = results.hand_landmarks[0][8]
                # Pass normalized coordinates to the controller
                controller.move_pointer(index_finger_tip.x, index_finger_tip.y)
        else:
            # Pass None so the recognizer can clear its history if the hand leaves the frame
            action_gesture = recognizer.recognize(None)

        # Draw the detected gesture on the screen (Debug Overlay)
        cv2.putText(img, f'Raw: {recognizer.raw_gesture}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(img, f'Confirmed: {recognizer.confirmed_gesture}', (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        
        cooldown_color = (0, 0, 255) if recognizer.is_cooldown else (0, 255, 0)
        cv2.putText(img, f'Cooldown: {recognizer.is_cooldown}', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cooldown_color, 2, cv2.LINE_AA)
        
        release_color = (0, 165, 255) if recognizer.waiting_for_release else (0, 255, 0)
        cv2.putText(img, f'Wait Release: {recognizer.waiting_for_release}', (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, release_color, 2, cv2.LINE_AA)
        
        cv2.putText(img, f'Action: {action_gesture}', (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2, cv2.LINE_AA)

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
