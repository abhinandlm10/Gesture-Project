import pyautogui
import time

class PresentationController:
    def __init__(self, smoothing=0.7):
        # Disable pyautogui failsafe to prevent crashes if cursor goes to corners
        pyautogui.FAILSAFE = False
        
        # Get actual screen size dynamically
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Controller-level cooldown
        self.last_action_time = 0
        self.action_cooldown = 1.0
        
        # Smoothing variables for pointer
        self.smoothing = smoothing
        self.prev_x = 0
        self.prev_y = 0
        self.first_move = True
        
    def next_slide(self):
        """Simulates pressing the Right Arrow key."""
        current_time = time.time()
        if current_time - self.last_action_time > self.action_cooldown:
            print("Action: Next Slide -> Pressing Right Arrow")
            pyautogui.press('right')
            self.last_action_time = current_time

    def previous_slide(self):
        """Simulates pressing the Left Arrow key."""
        current_time = time.time()
        if current_time - self.last_action_time > self.action_cooldown:
            print("Action: Previous Slide -> Pressing Left Arrow")
            pyautogui.press('left')
            self.last_action_time = current_time
            
    def move_pointer(self, x_norm, y_norm):
        """
        Moves the mouse cursor to a specific screen coordinate with smoothing.
        x_norm and y_norm should be normalized coordinates (0.0 to 1.0).
        """
        screen_x = int(x_norm * self.screen_width)
        screen_y = int(y_norm * self.screen_height)
        
        if self.first_move:
            self.prev_x = screen_x
            self.prev_y = screen_y
            self.first_move = False
            
        # Exponential Moving Average (EMA) for smoothing
        smooth_x = int(self.prev_x * self.smoothing + screen_x * (1 - self.smoothing))
        smooth_y = int(self.prev_y * self.smoothing + screen_y * (1 - self.smoothing))
        
        self.prev_x = smooth_x
        self.prev_y = smooth_y
        
        # Move mouse
        pyautogui.moveTo(smooth_x, smooth_y, duration=0)
