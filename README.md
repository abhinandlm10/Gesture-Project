# Smart Gesture & Voice-Controlled Presentation System

An AI-powered multimodal presentation control system featuring **Gesture Recognition** via webcam and **Voice Command Control** via microphone, allowing presenters to control slide decks seamlessly without touching the keyboard or mouse.

---

## Features & Input Modalities

### 1. Gesture Recognition (MediaPipe + Computer Vision)
The system uses computer vision with MediaPipe hand landmark tracking:
- 👍 **Thumbs Up**: Move to Next Slide (`Right Arrow`)
- 👎 **Thumbs Down**: Move to Previous Slide (`Left Arrow`)
- ✌️ **Two Fingers**: Capture Screenshot (saved to `screenshots/` directory with audio and toast notification)
- ☝️ **Index Pointing**: Interactive virtual pointer / mouse cursor control

> *Note: Gesture actions are active when the Presentation Timer is running.*

### 2. Voice Command Control (Microphone Recognition)
Control slides using natural spoken commands through your computer microphone. Includes controlled listening and debouncing to prevent accidental repetitions.

| Spoken Voice Command | Variations Allowed | Presentation Action | PowerPoint Effect |
|----------------------|-------------------|---------------------|-------------------|
| **"Next slide"** | "next", "go to next slide", "go next", "next page", "forward", "advance" | `NEXT_SLIDE` | Advances to the next slide (`Right Arrow`) |
| **"Previous slide"** | "previous", "go to previous slide", "go previous", "prev", "back", "go back" | `PREVIOUS_SLIDE` | Returns to previous slide (`Left Arrow`) |
| **"Go to slide [N]"** | "goto slide 10", "slide 5", "page 12", "jump to slide 42", "go to slide ten" | `GOTO_SLIDE` | Jumps directly to slide N (`[N] + Enter`) |
| **"Slide show"** | "slideshow", "start slide show", "start presentation", "begin presentation" | `START_SLIDESHOW` | Starts slideshow from beginning (`F5`) |
| **"Exit slideshow"** | "stop slide show", "end slideshow", "close presentation", "stop presentation" | `END_SLIDESHOW` | Exits slideshow mode (`Esc`) |
| **"Take screenshot"** | "screenshot", "capture screenshot", "capture screen", "snapshot" | `SCREENSHOT` | Saves screenshot with notification |

---

## System Architecture

The architecture maintains clean separation between gesture and voice modalities, uniting them through a central `ActionManager` that commands the underlying `PresentationController`:

```
           Webcam                                Microphone
             │                                       │
       HandTracker &                           VoiceCommandRecognizer
     GestureRecognizer                              (Rule-based)
             │                                       │
        VideoThread                             VoiceThread
             │                                       │
        (Gesture Cmd)                           (Voice Cmd)
             └───────────────────┬───────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │  ActionManager  │
                        └─────────────────┘
                                 │
                                 ▼
                     PresentationController
                   (pyautogui / screenshots)
                                 │
                                 ▼
                        PowerPoint Slides
```

---

## Installation & Setup

1. **Clone the repository and install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Requirements**:
   - `opencv-python`: Camera capture and frame processing
   - `mediapipe`: Hand landmark tracking
   - `pyautogui`: Slide control keystroke automation
   - `plyer`: Desktop toast notifications
   - `PySide6`: Modern desktop GUI application
   - `SpeechRecognition`: Audio capture and speech recognition
   - `pyaudio`: Microphone streaming interface

3. **Run the Application**:
   ```bash
   python src/main.py
   ```

---

## Voice Control Usage Guide

1. In the right panel under **Voice Control**, click **🎤 Voice Control: OFF** to toggle it to **ON**.
2. The status indicator will switch to **Listening...**.
3. Speak any supported command (e.g., *"Next slide"*, *"Previous slide"*, *"Take screenshot"*).
4. The system will recognize the command, provide feedback on the status panel, and trigger the action.
5. Click the toggle again to turn Voice Control **OFF** when chatting or during Q&A to avoid false triggers.

---

## Running Automated Tests

Run the full automated test suite covering command variations, debouncing, coexistence, and GUI lifecycle:
```bash
python -m unittest discover tests
python tests/test_gui.py
```
