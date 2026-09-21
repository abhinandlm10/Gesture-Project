import sys
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QGroupBox, QPushButton, QFormLayout, QFrame, QComboBox,
    QScrollArea, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QPixmap, QImage, QFont
from gui.video_thread import VideoThread
from voice.voice_thread import VoiceThread
from control.action_manager import ActionManager

class MainWindow(QMainWindow):
    """
    Modern Presentation Studio Interface.
    Features a responsive, high-aesthetic layout with camera HUD overlay,
    crisp presentation timer, tabbed control deck, and optimized fullscreen scaling.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Gesture Studio - Presentation Controller")
        self.resize(1140, 740)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(self._get_dark_stylesheet())
        
        # Main Central Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 12, 16, 16)
        root_layout.setSpacing(12)
        
        # --- 1. Top Header Bar ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title_label = QLabel("⚡ Smart Gesture Studio")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #38BDF8; letter-spacing: 0.5px;")

        self.session_badge = QLabel("● READY")
        self.session_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.session_badge.setStyleSheet(
            "background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; "
            "padding: 3px 10px; border-radius: 10px;"
        )

        self.fullscreen_btn = QPushButton("⛶ Fullscreen (F11)")
        self.fullscreen_btn.setFont(QFont("Segoe UI", 9))
        self.fullscreen_btn.setCursor(Qt.PointingHandCursor)
        self.fullscreen_btn.setStyleSheet(
            "QPushButton { background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; "
            "padding: 5px 12px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #334155; color: #F8FAFC; }"
        )
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.session_badge)
        header_layout.addStretch(1)
        header_layout.addWidget(self.fullscreen_btn)
        root_layout.addWidget(header_widget)

        # --- 2. Main Body (Horizontal Split) ---
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)
        root_layout.addLayout(body_layout, stretch=1)

        # --- LEFT SIDE: Video Card & HUD (Expands flexibly in fullscreen) ---
        video_section = QVBoxLayout()
        video_section.setSpacing(10)

        video_card = QFrame()
        video_card.setObjectName("videoCard")
        video_card.setStyleSheet(
            "QFrame#videoCard { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 12px; }"
        )
        video_card_layout = QVBoxLayout(video_card)
        video_card_layout.setContentsMargins(12, 10, 12, 12)
        video_card_layout.setSpacing(8)

        # Top bar inside video card: camera badge
        cam_header = QHBoxLayout()
        self.cam_badge = QLabel("● CAMERA FEED - READY")
        self.cam_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.cam_badge.setStyleSheet("color: #64748B; padding: 2px 4px;")
        cam_header.addWidget(self.cam_badge)
        cam_header.addStretch(1)
        video_card_layout.addLayout(cam_header)

        # Video Label (responsive, aspect-ratio preserved)
        self.video_label = QLabel("Initializing Webcam...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #070B13; border-radius: 8px; color: #64748B;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(480, 360)
        video_card_layout.addWidget(self.video_label, stretch=1)

        # Bottom HUD Banner inside video card
        hud_frame = QFrame()
        hud_frame.setStyleSheet(
            "background-color: rgba(15, 23, 42, 0.95); border: 1px solid #1E293B; "
            "border-radius: 8px; padding: 6px 12px;"
        )
        hud_layout = QHBoxLayout(hud_frame)
        hud_layout.setContentsMargins(8, 4, 8, 4)

        # Left side: Main Status Label
        self.status_label = QLabel("Status: Ready (Click Start to Activate)")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.status_label.setStyleSheet("color: #F59E0B;")
        hud_layout.addWidget(self.status_label)
        hud_layout.addStretch(1)

        # Right side: Modality indicator
        self.hud_modality_badge = QLabel("Modality: Gesture + Voice")
        self.hud_modality_badge.setFont(QFont("Segoe UI", 9))
        self.hud_modality_badge.setStyleSheet("color: #64748B;")
        hud_layout.addWidget(self.hud_modality_badge)

        video_card_layout.addWidget(hud_frame)
        video_section.addWidget(video_card, stretch=1)
        body_layout.addLayout(video_section, stretch=1)

        # --- RIGHT SIDE: Controls & Settings (Fixed optimal width, scrollable) ---
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setFixedWidth(390)
        sidebar_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 4, 0)
        right_panel_layout.setSpacing(14)

        # 1. Hero Presentation Timer Card
        timer_card = QFrame()
        timer_card.setStyleSheet(
            "background-color: #111827; border: 1px solid #1E293B; border-radius: 10px; padding: 10px;"
        )
        timer_layout = QVBoxLayout(timer_card)
        timer_layout.setSpacing(10)

        timer_title = QLabel("⏱️  PRESENTATION TIMER")
        timer_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        timer_title.setStyleSheet("color: #94A3B8; letter-spacing: 1px;")
        timer_layout.addWidget(timer_title)

        self.time_display = QLabel("00:00:00")
        self.time_display.setAlignment(Qt.AlignCenter)
        self.time_display.setFont(QFont("Consolas", 32, QFont.Bold))
        self.time_display.setStyleSheet(
            "color: #38BDF8; background-color: #070B13; border: 1px solid #1E293B; "
            "padding: 8px; border-radius: 8px; letter-spacing: 2px;"
        )
        timer_layout.addWidget(self.time_display)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; border: none; padding: 10px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #10B981; } "
            "QPushButton:pressed { background-color: #047857; }"
        )

        self.stop_btn = QPushButton("⏸  Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #D97706; color: white; border: none; padding: 10px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #F59E0B; } "
            "QPushButton:pressed { background-color: #B45309; }"
        )

        self.reset_btn = QPushButton("↺  Reset")
        self.reset_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet(
            "QPushButton { background-color: #334155; color: #E2E8F0; border: none; padding: 10px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #475569; } "
            "QPushButton:pressed { background-color: #1E293B; }"
        )

        self.start_btn.clicked.connect(self.start_timer)
        self.stop_btn.clicked.connect(self.stop_timer)
        self.reset_btn.clicked.connect(self.reset_timer)

        btn_layout.addWidget(self.start_btn, stretch=1)
        btn_layout.addWidget(self.stop_btn, stretch=1)
        btn_layout.addWidget(self.reset_btn, stretch=1)
        timer_layout.addLayout(btn_layout)
        right_panel_layout.addWidget(timer_card)

        # 2. Modern Tabbed Control Deck
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._get_tabs_stylesheet())

        # --- Tab 1: 🎮 Gestures ---
        gesture_tab = QWidget()
        gesture_tab_layout = QVBoxLayout(gesture_tab)
        gesture_tab_layout.setContentsMargins(10, 12, 10, 10)
        gesture_tab_layout.setSpacing(12)

        # Live Detection Status Card
        state_card = QFrame()
        state_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        state_card_layout = QVBoxLayout(state_card)
        state_card_layout.setSpacing(6)
        
        state_header = QLabel("LIVE GESTURE STATE")
        state_header.setFont(QFont("Segoe UI", 8, QFont.Bold))
        state_header.setStyleSheet("color: #64748B; letter-spacing: 0.5px;")
        state_card_layout.addWidget(state_header)

        self.lbl_confirmed = QLabel("Confirmed: None (Paused)")
        self.lbl_confirmed.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_cooldown = QLabel("Cooldown: <span style='color:#888888;'>Paused</span>")
        self.lbl_wait_release = QLabel("Waiting for Release: <span style='color:#888888;'>False</span>")

        state_card_layout.addWidget(self.lbl_confirmed)
        state_card_layout.addWidget(self.lbl_cooldown)
        state_card_layout.addWidget(self.lbl_wait_release)
        gesture_tab_layout.addWidget(state_card)

        # Gesture Mappings Card
        mapping_card = QFrame()
        mapping_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        mapping_layout = QFormLayout(mapping_card)
        mapping_layout.setSpacing(8)

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

        mapping_layout.addRow("Next Slide (👍):", self.combo_next)
        mapping_layout.addRow("Previous Slide (👎):", self.combo_prev)
        mapping_layout.addRow("Screenshot (✌️):", self.combo_screen)
        mapping_layout.addRow("Pointer (☝️):", self.combo_pointer)
        gesture_tab_layout.addWidget(mapping_card)
        gesture_tab_layout.addStretch(1)

        self.tabs.addTab(gesture_tab, "🎮 Gestures")

        # --- Tab 2: 🎙️ Voice Studio ---
        voice_tab = QWidget()
        voice_tab_layout = QVBoxLayout(voice_tab)
        voice_tab_layout.setContentsMargins(10, 12, 10, 10)
        voice_tab_layout.setSpacing(12)

        # Voice Master Toggle Button
        self.voice_toggle_btn = QPushButton("🎤 Voice Control: ON")
        self.voice_toggle_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.voice_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.voice_toggle_btn.setCheckable(True)
        self.voice_toggle_btn.setChecked(True)
        self.voice_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #059669; color: #ffffff; border: 1px solid #10B981; padding: 10px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #10B981; }"
        )
        self.voice_toggle_btn.clicked.connect(self.toggle_voice_control)
        voice_tab_layout.addWidget(self.voice_toggle_btn)

        # Live Voice Feedback Card
        voice_feedback_card = QFrame()
        voice_feedback_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        vfb_layout = QVBoxLayout(voice_feedback_card)
        vfb_layout.setSpacing(6)

        self.lbl_voice_status = QLabel("Status: Armed (Click Start)")
        self.lbl_voice_status.setFont(QFont("Segoe UI", 9))
        self.lbl_voice_status.setStyleSheet("color: #F59E0B;")

        self.lbl_voice_command = QLabel("Command: None")
        self.lbl_voice_command.setFont(QFont("Segoe UI", 9))
        self.lbl_voice_command.setStyleSheet("color: #94A3B8;")

        vfb_layout.addWidget(self.lbl_voice_status)
        vfb_layout.addWidget(self.lbl_voice_command)
        voice_tab_layout.addWidget(voice_feedback_card)

        # Supported Voice Commands Guide
        cmd_card = QFrame()
        cmd_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        cmd_layout = QVBoxLayout(cmd_card)
        cmd_layout.setSpacing(5)
        
        cmd_title = QLabel("SUPPORTED VOICE PHRASES")
        cmd_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        cmd_title.setStyleSheet("color: #64748B; letter-spacing: 0.5px;")
        cmd_layout.addWidget(cmd_title)

        hint1 = QLabel("• <b>Next Slide</b>: <i>'next', 'advance', 'next page', 'forward'</i>")
        hint1.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        hint2 = QLabel("• <b>Previous Slide</b>: <i>'previous', 'go back', 'prior', 'prev'</i>")
        hint2.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        hint3 = QLabel("• <b>Go to Slide</b>: <i>'go to slide 10', 'slide 5', 'page 12'</i>")
        hint3.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        hint4 = QLabel("• <b>Slide Show</b>: <i>'slide show', 'start presentation', 'exit slideshow'</i>")
        hint4.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        hint5 = QLabel("• <b>Screenshot</b>: <i>'take screenshot', 'capture screen', 'snapshot'</i>")
        hint5.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")

        cmd_layout.addWidget(hint1)
        cmd_layout.addWidget(hint2)
        cmd_layout.addWidget(hint3)
        cmd_layout.addWidget(hint4)
        cmd_layout.addWidget(hint5)
        voice_tab_layout.addWidget(cmd_card)
        voice_tab_layout.addStretch(1)

        self.tabs.addTab(voice_tab, "🎙️ Voice")

        # --- Tab 3: ⚙️ Settings ---
        settings_tab = QWidget()
        settings_tab_layout = QVBoxLayout(settings_tab)
        settings_tab_layout.setContentsMargins(10, 12, 10, 10)
        settings_tab_layout.setSpacing(12)

        sliders_card = QFrame()
        sliders_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px;")
        settings_layout = QFormLayout(sliders_card)
        settings_layout.setSpacing(10)

        # Smoothing Slider
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(0, 95)  # 0.0 to 0.95
        self.smooth_slider.setValue(70)     # Default 0.70
        self.smooth_slider.valueChanged.connect(self.update_smoothing)
        self.smooth_label = QLabel("0.70")
        self.smooth_label.setStyleSheet("color: #38BDF8; font-weight: bold;")

        # Cooldown Slider
        self.cooldown_slider = QSlider(Qt.Horizontal)
        self.cooldown_slider.setRange(5, 30)  # 0.5s to 3.0s
        self.cooldown_slider.setValue(10)     # Default 1.0s
        self.cooldown_slider.valueChanged.connect(self.update_cooldown)
        self.cooldown_label = QLabel("1.0s")
        self.cooldown_label.setStyleSheet("color: #38BDF8; font-weight: bold;")

        # Voice Cooldown Slider
        self.voice_cooldown_slider = QSlider(Qt.Horizontal)
        self.voice_cooldown_slider.setRange(2, 20)  # 0.2s to 2.0s
        self.voice_cooldown_slider.setValue(5)      # Default 0.5s
        self.voice_cooldown_slider.valueChanged.connect(self.update_voice_cooldown)
        self.voice_cooldown_label = QLabel("0.5s")
        self.voice_cooldown_label.setStyleSheet("color: #38BDF8; font-weight: bold;")

        settings_layout.addRow("Pointer Smoothing:", self.smooth_slider)
        settings_layout.addRow("", self.smooth_label)
        settings_layout.addRow("Gesture Cooldown:", self.cooldown_slider)
        settings_layout.addRow("", self.cooldown_label)
        settings_layout.addRow("Voice Cooldown:", self.voice_cooldown_slider)
        settings_layout.addRow("", self.voice_cooldown_label)

        settings_tab_layout.addWidget(sliders_card)
        settings_tab_layout.addStretch(1)

        self.tabs.addTab(settings_tab, "⚙️ Settings")

        right_panel_layout.addWidget(self.tabs)
        right_panel_layout.addStretch(1)

        sidebar_scroll.setWidget(right_panel)
        body_layout.addWidget(sidebar_scroll)

        # --- Internal State & Timers ---
        self.timer_active = False
        self.timer_seconds = 0
        self.last_voice_action_display_time = 0.0
        self.last_voice_action_text = ""
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.tick_timer)
        self.update_timer.setInterval(1000) # 1 second tick
        
        # --- Shared Action Manager & Threads ---
        self.action_manager = ActionManager()

        # Video Thread Initialization
        self.video_thread = VideoThread(action_manager=self.action_manager)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.update_gesture_signal.connect(self.update_gesture_info)
        self.video_thread.start()

        # Voice Thread Initialization
        self.voice_thread = VoiceThread(cooldown_time=0.5)
        self.voice_thread.command_detected.connect(self.on_voice_command)
        self.voice_thread.status_changed.connect(self.on_voice_status_changed)
        self.voice_thread.error_occurred.connect(self.on_voice_error)
        self.voice_thread.start()

    def toggle_fullscreen(self):
        """Toggles between standard window and maximized full-screen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("⛶ Fullscreen (F11)")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛶ Exit Fullscreen (Esc)")

    def keyPressEvent(self, event):
        """Keyboard shortcuts: F11 or Esc to toggle/exit full-screen."""
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def _get_dark_stylesheet(self):
        return """
        QMainWindow {
            background-color: #0B0F19;
            color: #F8FAFC;
        }
        QWidget {
            color: #F8FAFC;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Arial;
            font-size: 10pt;
        }
        QFrame {
            border: none;
        }
        QScrollBar:vertical {
            background: #0B0F19;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #334155;
            min-height: 24px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #475569;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QSlider::groove:horizontal {
            border: 1px solid #1E293B;
            height: 6px;
            background: #0F172A;
            border-radius: 3px;
        }
        QSlider::sub-page:horizontal {
            background: #0284C7;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #38BDF8;
            border: 2px solid #0EA5E9;
            width: 16px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #7DD3FC;
            border: 2px solid #38BDF8;
        }
        QComboBox {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 6px 10px;
            border-radius: 6px;
            color: #F8FAFC;
        }
        QComboBox:hover {
            border: 1px solid #0284C7;
        }
        QComboBox QAbstractItemView {
            background-color: #0F172A;
            border: 1px solid #334155;
            selection-background-color: #0284C7;
            selection-color: white;
            color: #F8FAFC;
            padding: 4px;
        }
        QLabel {
            color: #E2E8F0;
        }
        """

    def _get_tabs_stylesheet(self):
        return """
        QTabWidget::pane {
            border: 1px solid #1E293B;
            background-color: #111827;
            border-radius: 10px;
            top: -1px;
        }
        QTabBar::tab {
            background-color: #0F172A;
            color: #94A3B8;
            padding: 8px 14px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 3px;
            font-weight: bold;
            font-size: 9pt;
            border: 1px solid transparent;
        }
        QTabBar::tab:hover {
            background-color: #1E293B;
            color: #F8FAFC;
        }
        QTabBar::tab:selected {
            background-color: #111827;
            color: #38BDF8;
            border: 1px solid #1E293B;
            border-bottom: 2px solid #38BDF8;
        }
        """

    @Slot(QImage)
    def update_image(self, qt_img):
        """Updates the image label with a new opencv frame scaled to fit gracefully"""
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    @Slot(str, str, bool, bool)
    def update_gesture_info(self, action_gesture, confirmed, is_cooldown, wait_release):
        """Updates the status UI from the video thread"""
        if not self.timer_active:
            self.lbl_confirmed.setText("Confirmed: None (Paused)")
            self.lbl_cooldown.setText("Cooldown: <span style='color:#888888;'>Paused</span>")
            self.lbl_wait_release.setText("Waiting for Release: <span style='color:#888888;'>False</span>")
            self.status_label.setText("Status: PAUSED (Click Start to Activate)")
            self.status_label.setStyleSheet("color: #F59E0B;")
            return

        self.lbl_confirmed.setText(f"Confirmed: {confirmed}")
        
        # Color coding for debug panel
        cool_color = "#EF4444" if is_cooldown else "#10B981"
        self.lbl_cooldown.setText(f"Cooldown: <span style='color:{cool_color}'>{is_cooldown}</span>")
        
        rel_color = "#F59E0B" if wait_release else "#10B981"
        self.lbl_wait_release.setText(f"Waiting for Release: <span style='color:{rel_color}'>{wait_release}</span>")
        
        # Main Status
        if time.time() - self.last_voice_action_display_time < 2.0:
            self.status_label.setText(self.last_voice_action_text)
            self.status_label.setStyleSheet("color: #38BDF8;")
        elif action_gesture != "None":
            self.status_label.setText(f"Action: {action_gesture}")
            self.status_label.setStyleSheet("color: #38BDF8;")
        else:
            self.status_label.setText("Status: Monitoring...")
            self.status_label.setStyleSheet("color: #10B981;")

    # --- Voice Control Handlers ---
    def toggle_voice_control(self):
        is_active = self.voice_toggle_btn.isChecked()
        if is_active:
            self.voice_toggle_btn.setText("🎤 Voice Control: ON")
            self.voice_toggle_btn.setStyleSheet(
                "QPushButton { background-color: #059669; color: #ffffff; border: 1px solid #10B981; padding: 10px; border-radius: 6px; } "
                "QPushButton:hover { background-color: #10B981; }"
            )
            if self.timer_active:
                self.voice_thread.set_listening(True)
                self.lbl_voice_status.setText("Status: Listening...")
                self.lbl_voice_status.setStyleSheet("color: #10B981;")
            else:
                self.voice_thread.set_listening(False)
                self.lbl_voice_status.setText("Status: Armed (Click Start)")
                self.lbl_voice_status.setStyleSheet("color: #F59E0B;")
        else:
            self.voice_toggle_btn.setText("🎤 Voice Control: OFF")
            self.voice_toggle_btn.setStyleSheet(
                "QPushButton { background-color: #1E293B; color: #64748B; border: 1px solid #334155; padding: 10px; border-radius: 6px; } "
                "QPushButton:hover { background-color: #334155; }"
            )
            self.voice_thread.set_listening(False)
            self.lbl_voice_status.setText("Status: Disabled")
            self.lbl_voice_status.setStyleSheet("color: #64748B;")

    @Slot(str, str)
    def on_voice_command(self, action_name, spoken_text):
        """Executed when a valid voice command is recognized."""
        if not self.timer_active:
            print(f"[MainWindow] Ignored voice command '{action_name}': session is PAUSED/STOPPED (Click Start).")
            self.lbl_voice_command.setText(f"Command: <span style='color:#F59E0B;'>{action_name} (Ignored - Stopped)</span>")
            return

        executed = self.action_manager.execute_action(action_name, source="Voice")
        if executed:
            display_action = action_name
            if action_name.startswith("GOTO_SLIDE:"):
                slide_num = action_name.split(":")[1]
                display_action = f"Go To Slide {slide_num}"
            elif action_name == "START_SLIDESHOW":
                display_action = "Start Slideshow (F5)"
            elif action_name == "END_SLIDESHOW":
                display_action = "Exit Slideshow (Esc)"

            self.lbl_voice_command.setText(f"Command: <span style='color:#38BDF8; font-weight:bold;'>{display_action}</span> (\"{spoken_text}\")")
            self.last_voice_action_text = f"Voice Action: {display_action} (\"{spoken_text}\")"
            self.last_voice_action_display_time = time.time()
            self.status_label.setText(self.last_voice_action_text)
            self.status_label.setStyleSheet("color: #38BDF8;")

    @Slot(str)
    def on_voice_status_changed(self, status_msg):
        self.lbl_voice_status.setText(f"Status: {status_msg}")
        if "Listening" in status_msg:
            self.lbl_voice_status.setStyleSheet("color: #10B981;")
        elif "Recognizing" in status_msg:
            self.lbl_voice_status.setStyleSheet("color: #38BDF8;")
        elif "Unavailable" in status_msg or "error" in status_msg.lower() or "missing" in status_msg.lower():
            self.lbl_voice_status.setStyleSheet("color: #EF4444;")
        elif "Cooldown" in status_msg:
            self.lbl_voice_status.setStyleSheet("color: #F59E0B;")
        else:
            self.lbl_voice_status.setStyleSheet("color: #E2E8F0;")

    @Slot(str)
    def on_voice_error(self, err_msg):
        print(f"[MainWindow] Voice error: {err_msg}")
        self.lbl_voice_status.setText(f"Error: {err_msg}")
        self.lbl_voice_status.setStyleSheet("color: #EF4444;")

    # --- Timer Controls ---
    def start_timer(self):
        if not self.timer_active:
            self.update_timer.start()
            self.timer_active = True
            self.session_badge.setText("● ACTIVE")
            self.session_badge.setStyleSheet(
                "background-color: #064E3B; color: #34D399; border: 1px solid #059669; "
                "padding: 3px 10px; border-radius: 10px;"
            )
            self.cam_badge.setText("● CAMERA FEED - ACTIVE")
            self.cam_badge.setStyleSheet("color: #34D399; padding: 2px 4px;")
            self.video_thread.set_gestures_active(True)
            if self.voice_toggle_btn.isChecked():
                self.voice_thread.set_listening(True)
                self.lbl_voice_status.setText("Status: Listening...")
                self.lbl_voice_status.setStyleSheet("color: #10B981;")
            self.status_label.setText("Status: Monitoring...")
            self.status_label.setStyleSheet("color: #10B981;")

    def stop_timer(self):
        if self.timer_active:
            self.update_timer.stop()
            self.timer_active = False
            self.session_badge.setText("⏸ PAUSED")
            self.session_badge.setStyleSheet(
                "background-color: #451A03; color: #FBBF24; border: 1px solid #D97706; "
                "padding: 3px 10px; border-radius: 10px;"
            )
            self.cam_badge.setText("● CAMERA FEED - PAUSED")
            self.cam_badge.setStyleSheet("color: #FBBF24; padding: 2px 4px;")
            self.video_thread.set_gestures_active(False)
            self.voice_thread.set_listening(False)
            self.status_label.setText("Status: PAUSED (Click Start to Activate)")
            self.status_label.setStyleSheet("color: #F59E0B;")
            if self.voice_toggle_btn.isChecked():
                self.lbl_voice_status.setText("Status: Paused (Click Start)")
                self.lbl_voice_status.setStyleSheet("color: #F59E0B;")
            else:
                self.lbl_voice_status.setText("Status: Disabled")
                self.lbl_voice_status.setStyleSheet("color: #64748B;")

    def reset_timer(self):
        self.stop_timer()
        self.timer_seconds = 0
        self.update_timer_display()
        self.session_badge.setText("● READY")
        self.session_badge.setStyleSheet(
            "background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; "
            "padding: 3px 10px; border-radius: 10px;"
        )
        self.cam_badge.setText("● CAMERA FEED - READY")
        self.cam_badge.setStyleSheet("color: #64748B; padding: 2px 4px;")
        self.video_thread.set_gestures_active(False)
        self.voice_thread.set_listening(False)
        self.status_label.setText("Status: STOPPED (Click Start to Activate)")
        self.status_label.setStyleSheet("color: #F59E0B;")
        self.lbl_confirmed.setText("Confirmed: None")
        self.lbl_cooldown.setText("Cooldown: False")
        self.lbl_wait_release.setText("Waiting for Release: False")
        self.lbl_voice_command.setText("Command: None")
        if self.voice_toggle_btn.isChecked():
            self.lbl_voice_status.setText("Status: Armed (Click Start)")
            self.lbl_voice_status.setStyleSheet("color: #F59E0B;")
        else:
            self.lbl_voice_status.setText("Status: Disabled")
            self.lbl_voice_status.setStyleSheet("color: #64748B;")

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

    def update_voice_cooldown(self, value):
        val_float = value / 10.0
        self.voice_cooldown_label.setText(f"{val_float:.1f}s")
        self.voice_thread.set_cooldown(val_float)

    def closeEvent(self, event):
        """Clean up threads when closing the window"""
        self.video_thread.stop()
        self.voice_thread.stop()
        event.accept()
