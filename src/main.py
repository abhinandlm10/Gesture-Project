import cv2
import sys
import time
from vision.hand_tracker import HandTracker

def main():
    print("Initializing Smart Gesture Presentation System...")
    
    # Open the default webcam (index 0)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not access the webcam.")
        sys.exit(1)

    # Initialize the hand tracker with the new Tasks API
    try:
        tracker = HandTracker(max_num_hands=2, min_detection_confidence=0.7)
    except Exception as e:
        print(f"Error initializing hand tracker: {e}")
        sys.exit(1)

    print("Webcam started successfully.")
    print("--> Press 'q' or 'ESC' to exit.")

    start_time = time.time()

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

        # Process the image to find hands
        img, results = tracker.find_hands(img, timestamp_ms, draw=True)

        # Display the processed image in a window
        cv2.imshow("Gesture Presentation System - Phase 1", img)

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
