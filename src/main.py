import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    print("Starting Smart Gesture Presentation System (Phase 5 UI)...")
    
    # Start the Qt Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
