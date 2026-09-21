import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

def run_gui_test():
    try:
        from PySide6.QtWidgets import QApplication
        from gui.main_window import MainWindow

        app = QApplication.instance() or QApplication(sys.argv)
        print("Instantiating MainWindow...")
        window = MainWindow()
        print("MainWindow created successfully!")

        # Verify Voice UI components
        assert hasattr(window, 'voice_toggle_btn'), "Missing voice_toggle_btn"
        assert hasattr(window, 'lbl_voice_status'), "Missing lbl_voice_status"
        assert hasattr(window, 'lbl_voice_command'), "Missing lbl_voice_command"
        assert hasattr(window, 'voice_thread'), "Missing voice_thread"
        assert hasattr(window, 'action_manager'), "Missing action_manager"
        assert hasattr(window, 'video_thread'), "Missing video_thread"

        # Verify initial state: Paused until Start is clicked
        assert window.timer_active is False, "Timer should not be active initially"
        assert window.video_thread.gestures_active is False, "Gestures should be inactive initially"
        assert window.voice_thread.is_listening is False, "Voice should not be listening until Start"

        print("Testing voice command blocked while stopped...")
        window.on_voice_command("NEXT_SLIDE", "next slide")
        assert "Ignored" in window.lbl_voice_command.text(), "Command should be ignored when stopped"

        print("Testing Start Timer activation...")
        window.start_timer()
        assert window.timer_active is True, "Timer should be active after start_timer"
        assert window.video_thread.gestures_active is True, "Gestures should be active after start_timer"
        assert window.voice_thread.is_listening is True, "Voice should be listening after start_timer"

        print("Testing voice command execution while started...")
        window.on_voice_command("NEXT_SLIDE", "next slide")
        assert "NEXT_SLIDE" in window.lbl_voice_command.text()
        assert "NEXT_SLIDE" in window.status_label.text()

        print("Testing Stop Timer...")
        window.stop_timer()
        assert window.timer_active is False, "Timer should be inactive after stop_timer"
        assert window.video_thread.gestures_active is False, "Gestures should be inactive after stop_timer"
        assert window.voice_thread.is_listening is False, "Voice should be inactive after stop_timer"

        print("Testing voice command blocked after Stop...")
        window.on_voice_command("NEXT_SLIDE", "next slide")
        assert "Ignored" in window.lbl_voice_command.text(), "Command must be ignored after stop_timer"

        print("Testing Reset Timer...")
        window.reset_timer()
        assert window.timer_seconds == 0, "Timer seconds should be 0 after reset"
        assert window.timer_active is False, "Timer should be inactive after reset_timer"
        assert window.video_thread.gestures_active is False, "Gestures should be inactive after reset_timer"
        assert window.voice_thread.is_listening is False, "Voice should be inactive after reset_timer"

        print("Testing toggle OFF while running...")
        window.start_timer()
        assert window.voice_thread.is_listening is True
        window.voice_toggle_btn.setChecked(False)
        window.toggle_voice_control()
        assert window.voice_thread.is_listening is False, "Voice thread should be disabled when toggled OFF"

        print("Cleaning up threads...")
        window.stop_timer()
        window.video_thread._run_flag = False
        window.video_thread.wait(1000)
        window.voice_thread._run_flag = False
        window.voice_thread.wait(1000)
        print("GUI test completed successfully!")
        return 0
    except Exception:
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(run_gui_test())
