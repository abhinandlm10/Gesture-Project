import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from control.presentation_controller import PresentationController
from control.action_manager import ActionManager, PresentationAction
from voice.recognizer import VoiceCommandRecognizer
from voice.voice_thread import VoiceThread

class TestVoiceRecognitionAndActions(unittest.TestCase):

    def setUp(self):
        self.mock_controller = MagicMock(spec=PresentationController)
        self.action_manager = ActionManager(controller=self.mock_controller)
        self.recognizer = VoiceCommandRecognizer(cooldown_time=1.0)

    # 1. Test Command Matching & Variations
    def test_next_slide_variations(self):
        variations = [
            "next slide", "Next Slide", "NEXT SLIDE", "next",
            "go to next slide", "go next", "next page", "forward",
            "Please go to next slide!", "next please", "advance",
            "advance slide", "next one", "show next slide", "move forward"
        ]
        for phrase in variations:
            self.assertEqual(
                self.recognizer.parse_command(phrase),
                PresentationAction.NEXT_SLIDE,
                f"Failed matching '{phrase}' to NEXT_SLIDE"
            )

    def test_previous_slide_variations(self):
        variations = [
            "previous slide", "Previous Slide", "previous", "go to previous slide",
            "go previous", "prev", "back", "go back", "previous page",
            "Can you go back to previous slide?", "go back please", "previous please",
            "back please", "prior slide", "prior", "last page", "move back"
        ]
        for phrase in variations:
            self.assertEqual(
                self.recognizer.parse_command(phrase),
                PresentationAction.PREVIOUS_SLIDE,
                f"Failed matching '{phrase}' to PREVIOUS_SLIDE"
            )

    def test_screenshot_variations(self):
        variations = [
            "take screenshot", "take a screenshot", "capture screenshot",
            "screenshot", "screen capture", "capture screen", "snapshot",
            "Take screenshot now!", "screen shot", "take screen shot",
            "take a screen shot", "capture screen shot", "print screen",
            "screen grab", "could you take a screenshot"
        ]
        for phrase in variations:
            self.assertEqual(
                self.recognizer.parse_command(phrase),
                PresentationAction.SCREENSHOT,
                f"Failed matching '{phrase}' to SCREENSHOT"
            )

    # 2. Test Unrecognized Speech and Background Noise
    def test_unrecognized_speech_and_noise(self):
        noise_phrases = [
            "", " ", "   ", "hello everyone", "good morning",
            "let us look at this chart", "random conversation",
            "slides are nice", "cough", "humming",
            "in our next quarterly review we will discuss the business model"
        ]
        for phrase in noise_phrases:
            action, status = self.recognizer.recognize(phrase)
            self.assertIsNone(action, f"Phrase '{phrase}' should not trigger an action")
            self.assertEqual(status, "NO_MATCH")

    # 3. Test Debouncing / Cooldown
    def test_repeated_speech_cooldown(self):
        # First trigger should succeed
        action, status = self.recognizer.recognize("next slide")
        self.assertEqual(action, PresentationAction.NEXT_SLIDE)
        self.assertEqual(status, "TRIGGERED")

        # Immediate repeated call should be blocked
        action2, status2 = self.recognizer.recognize("next slide")
        self.assertIsNone(action2)
        self.assertTrue(status2.startswith("COOLDOWN"), f"Expected COOLDOWN status, got {status2}")

        # Another variation within cooldown window should also be blocked
        action3, status3 = self.recognizer.recognize("go to next slide")
        self.assertIsNone(action3)
        self.assertTrue(status3.startswith("COOLDOWN"))

        # Wait for cooldown to expire
        time.sleep(1.1)
        action4, status4 = self.recognizer.recognize("next slide")
        self.assertEqual(action4, PresentationAction.NEXT_SLIDE)
        self.assertEqual(status4, "TRIGGERED")

    def test_dynamic_cooldown_adjustment(self):
        """Test that set_cooldown allows reducing cooldown time dynamically."""
        self.recognizer.set_cooldown(0.3)
        action1, status1 = self.recognizer.recognize("next slide")
        self.assertEqual(action1, PresentationAction.NEXT_SLIDE)

        # Immediate repeat should be blocked
        action2, status2 = self.recognizer.recognize("next slide")
        self.assertIsNone(action2)
        self.assertTrue(status2.startswith("COOLDOWN"))

        # Wait only 0.35s (well below previous 1.0s/1.5s threshold)
        time.sleep(0.35)
        action3, status3 = self.recognizer.recognize("next slide")
        self.assertEqual(action3, PresentationAction.NEXT_SLIDE)
        self.assertEqual(status3, "TRIGGERED")

    def test_alternating_commands_fast_path(self):
        """Test that changing command types (e.g. NEXT -> SCREENSHOT) triggers quickly."""
        action1, status1 = self.recognizer.recognize("next slide")
        self.assertEqual(action1, PresentationAction.NEXT_SLIDE)

        # Wait brief period (> 0.3s fast path)
        time.sleep(0.32)
        action2, status2 = self.recognizer.recognize("take screenshot")
        self.assertEqual(action2, PresentationAction.SCREENSHOT)
        self.assertEqual(status2, "TRIGGERED")

    # 4. Test ActionManager routing and source tracking
    def test_action_manager_next_slide(self):
        result = self.action_manager.execute_action(PresentationAction.NEXT_SLIDE, source="Voice")
        self.assertTrue(result)
        self.mock_controller.next_slide.assert_called_once()
        self.assertEqual(self.action_manager.last_action, PresentationAction.NEXT_SLIDE)
        self.assertEqual(self.action_manager.last_action_source, "Voice")

    def test_action_manager_previous_slide(self):
        result = self.action_manager.execute_action(PresentationAction.PREVIOUS_SLIDE, source="Voice")
        self.assertTrue(result)
        self.mock_controller.previous_slide.assert_called_once()
        self.assertEqual(self.action_manager.last_action, PresentationAction.PREVIOUS_SLIDE)
        self.assertEqual(self.action_manager.last_action_source, "Voice")

    def test_action_manager_screenshot(self):
        result = self.action_manager.execute_action(PresentationAction.SCREENSHOT, source="Voice")
        self.assertTrue(result)
        self.mock_controller.take_screenshot.assert_called_once()
        self.assertEqual(self.action_manager.last_action, PresentationAction.SCREENSHOT)
        self.assertEqual(self.action_manager.last_action_source, "Voice")

    # 5. Coexistence: Gesture + Voice through ActionManager
    def test_gesture_and_voice_coexistence(self):
        # Gesture triggers next slide
        self.action_manager.execute_action(PresentationAction.NEXT_SLIDE, source="Gesture")
        self.mock_controller.next_slide.assert_called_once()
        self.assertEqual(self.action_manager.last_action_source, "Gesture")

        # Voice triggers previous slide
        self.action_manager.execute_action(PresentationAction.PREVIOUS_SLIDE, source="Voice")
        self.mock_controller.previous_slide.assert_called_once()
        self.assertEqual(self.action_manager.last_action_source, "Voice")

        # Gesture triggers screenshot
        self.action_manager.execute_action(PresentationAction.SCREENSHOT, source="Gesture")
        self.mock_controller.take_screenshot.assert_called_once()
        self.assertEqual(self.action_manager.last_action_source, "Gesture")

    # 6. Test Voice Control Toggle (Controlled Listening)
    def test_voice_thread_toggle_listening(self):
        thread = VoiceThread()
        self.assertFalse(thread.is_listening)

        # Enable listening
        thread.set_listening(True)
        self.assertTrue(thread.is_listening)

        # Disable listening
        thread.set_listening(False)
        self.assertFalse(thread.is_listening)

    # 7. Test Graceful Failure when Microphone is Unavailable
    @patch('speech_recognition.Microphone')
    def test_microphone_unavailable_stability(self, mock_mic):
        mock_mic.side_effect = Exception("No default input device available")
        thread = VoiceThread()
        
        status_updates = []
        error_updates = []
        thread.status_changed.connect(lambda s: status_updates.append(s))
        thread.error_occurred.connect(lambda e: error_updates.append(e))
        
        # Calling run with stop flag pre-set to avoid hanging
        thread._run_flag = False
        thread.run()

        self.assertTrue(any("Microphone Unavailable" in s for s in status_updates))
        self.assertTrue(any("Microphone init failed" in e for e in error_updates))

if __name__ == '__main__':
    unittest.main()
