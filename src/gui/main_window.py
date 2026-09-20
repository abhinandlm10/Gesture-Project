import sys
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QGroupBox, QPushButton, QFormLayout, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPixmap, QImage, QFont
from gui.video_thread import VideoThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Gesture Presentation System")
        self.resize(1000, 700)
        self.setStyleSheet(self._get_dark_stylesheet())
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # --- LEFT SIDE: Video Feed ---
        video_layout = QVBoxLayout()
        
        self.video_label = QLabel("Initializing Webcam...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #1e1e1e; border: 2px solid #3a3a3a; border-radius: 10px;")
        self.video_label.setMinimumSize(640, 480)
        
        video_layout.addWidget(self.video_label, stretch=1)
        
        # Status Label under video
        self.status_label = QLabel("Status: Waiting...")
        self.status_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #4CAF50;")
        video_layout.addWidget(self.status_label)
        
        main_layout.addLayout(video_layout, stretch=2)
        
        # --- RIGHT SIDE: Controls & Settings ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        
        # 1. Timer Group
        timer_group = QGroupBox("Presentation Timer")
        timer_layout = QVBoxLayout()
        
        self.time_display = QLabel("00:00:00")
        self.time_display.setAlignment(Qt.AlignCenter)
        self.time_display.setFont(QFont("Consolas", 36, QFont.Bold))
        self.time_display.setStyleSheet("color: #00E5FF; background: #121212; padding: 10px; border-radius: 5px;")
        
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.reset_btn = QPushButton("Reset")
        
        self.start_btn.clicked.connect(self.start_timer)
        self.stop_btn.clicked.connect(self.stop_timer)
        self.reset_btn.clicked.connect(self.reset_timer)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.reset_btn)
        
        timer_layout.addWidget(self.time_display)
        timer_layout.addLayout(btn_layout)
        timer_group.setLayout(timer_layout)
        right_panel.addWidget(timer_group)
        
        # 2. Settings Group
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()
        
        # Smoothing Slider
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(0, 95)  # 0.0 to 0.95
        self.smooth_slider.setValue(70)     # Default 0.7
        self.smooth_slider.valueChanged.connect(self.update_smoothing)
        self.smooth_label = QLabel("0.70")
        
        # Cooldown Slider
        self.cooldown_slider = QSlider(Qt.Horizontal)
        self.cooldown_slider.setRange(5, 30)  # 0.5s to 3.0s
        self.cooldown_slider.setValue(10)     # Default 1.0s
        self.cooldown_slider.valueChanged.connect(self.update_cooldown)
        self.cooldown_label = QLabel("1.0s")
        
        settings_layout.addRow("Pointer Smoothing:", self.smooth_slider)
        settings_layout.addRow("", self.smooth_label)
        settings_layout.addRow("Gesture Cooldown:", self.cooldown_slider)
        settings_layout.addRow("", self.cooldown_label)
        
        settings_group.setLayout(settings_layout)
        right_panel.addWidget(settings_group)
        
        # 3. Gesture Mapping Group
        mapping_group = QGroupBox("Gesture Mapping")
        mapping_layout = QFormLayout()
        
        gestures_list = ["THUMBS_UP", "THUMBS_DOWN", "TWO_FINGERS", "OPEN_PALM", "CLOSED_FIST", "INDEX_POINTING", "None"]
        
        self.combo_next = QComboBox()
        self.combo_next.addItems(gestures_list)
        self.combo_next.setCurrentText("THUMBS_UP")
        self.combo_next.currentTextChanged.connect(lambda text: self.video_thread.update_gesture_mapping("Next Slide", text))
        
        self.combo_prev = QComboBox()
        self.combo_prev.addItems(gestures_list)
        self.combo_prev.setCurrentText("THUMBS_DOWN")
        self.combo_prev.currentTextChanged.connect(lambda text: self.video_thread.update_gesture_mapping("Previous Slide", text))

        self.combo_screen = QComboBox()
        self.combo_screen.addItems(gestures_list)
        self.combo_screen.setCurrentText("TWO_FINGERS")
        self.combo_screen.currentTextChanged.connect(lambda text: self.video_thread.update_gesture_mapping("Screenshot", text))

        self.combo_pointer = QComboBox()
        self.combo_pointer.addItems(gestures_list)
        self.combo_pointer.setCurrentText("INDEX_POINTING")
        self.combo_pointer.currentTextChanged.connect(lambda text: self.video_thread.update_gesture_mapping("Pointer", text))

        mapping_layout.addRow("Next Slide:", self.combo_next)
        mapping_layout.addRow("Previous Slide:", self.combo_prev)
        mapping_layout.addRow("Screenshot:", self.combo_screen)
        mapping_layout.addRow("Pointer:", self.combo_pointer)
        
        mapping_group.setLayout(mapping_layout)
        right_panel.addWidget(mapping_group)
        
        # 4. Live Gesture State Group
        state_group = QGroupBox("Live Recognition State")
        state_layout = QVBoxLayout()
        self.lbl_confirmed = QLabel("Confirmed: None")
        self.lbl_cooldown = QLabel("Cooldown: False")
        self.lbl_wait_release = QLabel("Waiting for Release: False")
        
        state_layout.addWidget(self.lbl_confirmed)
        state_layout.addWidget(self.lbl_cooldown)
        state_layout.addWidget(self.lbl_wait_release)
        state_group.setLayout(state_layout)
        right_panel.addWidget(state_group)
        
        right_panel.addStretch(1)
        main_layout.addLayout(right_panel, stretch=1)
        
        # --- Internal State & Timers ---
        self.timer_active = False
        self.timer_seconds = 0
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.tick_timer)
        self.update_timer.setInterval(1000) # 1 second tick
        
        # --- Video Thread Initialization ---
        self.video_thread = VideoThread()
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.update_gesture_signal.connect(self.update_gesture_info)
        self.video_thread.start()

    def _get_dark_stylesheet(self):
        return """
        QMainWindow {
            background-color: #121212;
            color: #ffffff;
        }
        QWidget {
            color: #ffffff;
            font-family: "Segoe UI", Arial;
            font-size: 10pt;
        }
        QGroupBox {
            border: 1px solid #333333;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: #1e1e1e;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
            color: #bbbbbb;
        }
        QPushButton {
            background-color: #3a3a3a;
            border: 1px solid #555555;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
        QSlider::groove:horizontal {
            border: 1px solid #444;
            height: 8px;
            background: #2a2a2a;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #00E5FF;
            border: 1px solid #00B3CC;
            width: 14px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 7px;
        }
        QComboBox {
            background-color: #3a3a3a;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 4px;
        }
        QComboBox QAbstractItemView {
            background-color: #2a2a2a;
            selection-background-color: #00E5FF;
            selection-color: black;
        }
        QLabel {
            color: #e0e0e0;
        }
        """

    @Slot(QImage)
    def update_image(self, qt_img):
        """Updates the image label with a new opencv frame"""
        # Scale pixmap to fit the label, keeping aspect ratio
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    @Slot(str, str, bool, bool)
    def update_gesture_info(self, action_gesture, confirmed, is_cooldown, wait_release):
        """Updates the status UI from the video thread"""
        self.lbl_confirmed.setText(f"Confirmed: {confirmed}")
        
        # Color coding for debug panel
        cool_color = "#FF5252" if is_cooldown else "#4CAF50"
        self.lbl_cooldown.setText(f"Cooldown: <span style='color:{cool_color}'>{is_cooldown}</span>")
        
        rel_color = "#FFC107" if wait_release else "#4CAF50"
        self.lbl_wait_release.setText(f"Waiting for Release: <span style='color:{rel_color}'>{wait_release}</span>")
        
        # Main Status
        if not self.timer_active:
            self.status_label.setText("Status: Gestures PAUSED (Start Timer to Activate)")
            self.status_label.setStyleSheet("color: #FFC107;") # Amber/Warning
        elif action_gesture != "None":
            self.status_label.setText(f"Action: {action_gesture}")
            self.status_label.setStyleSheet("color: #00E5FF;") # Cyan highlight on action
        else:
            self.status_label.setText("Status: Monitoring...")
            self.status_label.setStyleSheet("color: #4CAF50;") # Green default

    # --- Timer Controls ---
    def start_timer(self):
        if not self.timer_active:
            self.update_timer.start()
            self.timer_active = True
            self.video_thread.set_gestures_active(True)

    def stop_timer(self):
        if self.timer_active:
            self.update_timer.stop()
            self.timer_active = False
            self.video_thread.set_gestures_active(False)

    def reset_timer(self):
        self.stop_timer()
        self.timer_seconds = 0
        self.update_timer_display()

    def tick_timer(self):
        self.timer_seconds += 1
        self.update_timer_display()

    def update_timer_display(self):
        h = self.timer_seconds // 3600
        m = (self.timer_seconds % 3600) // 60
        s = self.timer_seconds % 60
        self.time_display.setText(f"{h:02d}:{m:02d}:{s:02d}")

    # --- Settings Updaters ---
    def update_smoothing(self, value):
        val_float = value / 100.0
        self.smooth_label.setText(f"{val_float:.2f}")
        self.video_thread.set_smoothing(val_float)

    def update_cooldown(self, value):
        val_float = value / 10.0
        self.cooldown_label.setText(f"{val_float:.1f}s")
        self.video_thread.set_cooldown(val_float)

    def closeEvent(self, event):
        """Clean up threads when closing the window"""
        self.video_thread.stop()
        event.accept()
