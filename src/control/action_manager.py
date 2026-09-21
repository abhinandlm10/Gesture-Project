import re
import time
from control.presentation_controller import PresentationController

class PresentationAction:
    NEXT_SLIDE = "NEXT_SLIDE"
    PREVIOUS_SLIDE = "PREVIOUS_SLIDE"
    SCREENSHOT = "SCREENSHOT"
    START_SLIDESHOW = "START_SLIDESHOW"
    END_SLIDESHOW = "END_SLIDESHOW"
    GOTO_SLIDE = "GOTO_SLIDE"

class ActionManager:
    """
    Central action dispatcher for the presentation system.
    Receives commands from both Gesture Recognition and Voice Recognition,
    routing them to the single underlying PresentationController instance.
    """
    def __init__(self, controller=None):
        self.controller = controller if controller is not None else PresentationController(smoothing=0.7)
        self.last_action = "None"
        self.last_action_source = "None"
        self.last_action_time = 0.0

    def execute_action(self, action_name: str, source: str = "Unknown", **kwargs) -> bool:
        """
        Executes the specified presentation action if valid.
        
        Args:
            action_name: The action to perform (from PresentationAction or string name,
                         e.g. 'GOTO_SLIDE:10')
            source: The originating modality ('Gesture', 'Voice', etc.)
            **kwargs: Additional parameters (e.g. slide_number=10)
            
        Returns:
            bool: True if the action was executed, False otherwise.
        """
        action_name = action_name.strip()
        upper_name = action_name.upper()
        executed = False

        if upper_name == PresentationAction.NEXT_SLIDE:
            self.controller.next_slide()
            executed = True
        elif upper_name == PresentationAction.PREVIOUS_SLIDE:
            self.controller.previous_slide()
            executed = True
        elif upper_name == PresentationAction.SCREENSHOT:
            self.controller.take_screenshot()
            executed = True
        elif upper_name == PresentationAction.START_SLIDESHOW:
            self.controller.start_slideshow()
            executed = True
        elif upper_name == PresentationAction.END_SLIDESHOW:
            self.controller.end_slideshow()
            executed = True
        elif upper_name.startswith("GOTO_SLIDE"):
            slide_num = kwargs.get("slide_number", None)
            if slide_num is None:
                # Extract number from action_name e.g. "GOTO_SLIDE:10" or "GOTO_SLIDE 10"
                parts = re.split(r"[:\s]+", upper_name)
                if len(parts) > 1 and parts[1].isdigit():
                    slide_num = int(parts[1])
                else:
                    slide_num = 1
            self.controller.goto_slide(slide_num)
            executed = True
        else:
            print(f"[ActionManager] Warning: Unknown action '{action_name}' requested from source '{source}'")
            return False

        if executed:
            self.last_action = action_name
            self.last_action_source = source
            self.last_action_time = time.time()
            print(f"[ActionManager] Executed '{action_name}' triggered by '{source}'")

        return executed

    def move_pointer(self, x_norm: float, y_norm: float):
        """Delegates pointer movement to the controller."""
        self.controller.move_pointer(x_norm, y_norm)

    def release_pointer(self):
        """Delegates pointer release to the controller."""
        self.controller.release_pointer()

    def set_smoothing(self, value: float):
        """Updates controller smoothing parameter."""
        self.controller.smoothing = value
