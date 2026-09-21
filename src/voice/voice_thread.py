import queue
import threading
import time
from PySide6.QtCore import QThread, Signal
from voice.recognizer import VoiceCommandRecognizer

try:
    import speech_recognition as sr
    HAS_SPEECH_RECOGNITION = True
except ImportError:
    sr = None
    HAS_SPEECH_RECOGNITION = False

class VoiceThread(QThread):
    """
    Background worker thread that captures microphone audio and recognizes
    spoken presentation commands without blocking the GUI or camera feed.
    Uses continuous stream recording and asynchronous recognition to eliminate
    dead-zones between consecutive voice commands.
    """
    command_detected = Signal(str, str)   # (action_name, spoken_phrase)
    status_changed = Signal(str)          # status message for GUI display
    error_occurred = Signal(str)          # error description

    def __init__(self, cooldown_time: float = 0.5):
        super().__init__()
        self._run_flag = True
        self.is_listening = False
        
        self.matcher = VoiceCommandRecognizer(cooldown_time=cooldown_time)
        self.recognizer = None
        self.microphone = None
        self._mic_initialized = False

        self._audio_queue = queue.Queue(maxsize=2)
        self._worker_thread = None

    def set_cooldown(self, seconds: float):
        """Dynamically updates the voice command cooldown time."""
        self.matcher.set_cooldown(seconds)

    def set_listening(self, active: bool):
        """Toggles voice listening on or off."""
        self.is_listening = active
        if active:
            if not self._mic_initialized:
                self.status_changed.emit("Initializing microphone...")
            else:
                self.status_changed.emit("Listening for commands...")
        else:
            # Drain any pending audio when turning off listening
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break
            self.status_changed.emit("Voice Control: OFF")

    def _recognition_worker(self):
        """Dedicated worker thread that handles Google STT recognition asynchronously."""
        while self._run_flag:
            try:
                item = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            audio, capture_time = item

            # Drop stale audio if recognition got delayed by more than 3.5s
            if time.time() - capture_time > 3.5:
                continue

            if not self.is_listening or not self._run_flag:
                continue

            self.status_changed.emit("Recognizing...")
            try:
                spoken_text = self.recognizer.recognize_google(audio)
                print(f"[VoiceThread] Heard: '{spoken_text}'")

                action, status = self.matcher.recognize(spoken_text)

                if action:
                    print(f"[VoiceThread] Command matched: {action} from '{spoken_text}'")
                    self.command_detected.emit(action, spoken_text)
                    self.status_changed.emit(f"Recognized: '{spoken_text}' -> {action}")
                elif "COOLDOWN" in status:
                    print(f"[VoiceThread] Cooldown active for: '{spoken_text}'")
                    self.status_changed.emit(f"Cooldown active: '{spoken_text}'")
                else:
                    print(f"[VoiceThread] Unmatched speech: '{spoken_text}'")
                    self.status_changed.emit(f"Heard: '{spoken_text}' (No command)")

            except sr.UnknownValueError:
                # Speech was unintelligible or background noise
                if self.is_listening:
                    self.status_changed.emit("Listening...")
            except sr.RequestError as e:
                print(f"[VoiceThread] Speech Recognition API error: {e}")
                self.status_changed.emit("Voice: Network error")
                self.error_occurred.emit(f"Speech API network error: {e}")
                time.sleep(0.5)
            except Exception as e:
                print(f"[VoiceThread] Recognition processing error: {e}")

    def run(self):
        """Main audio capture loop keeping the microphone stream open continuously."""
        if not HAS_SPEECH_RECOGNITION:
            self.error_occurred.emit("SpeechRecognition library is not installed.")
            self.status_changed.emit("Voice: Library Missing")
            return

        # Initialize speech recognizer with optimized thresholds
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.5
        self.recognizer.phrase_threshold = 0.2
        self.recognizer.non_speaking_duration = 0.3
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        # Start asynchronous recognition worker thread
        self._worker_thread = threading.Thread(target=self._recognition_worker, daemon=True)
        self._worker_thread.start()

        # Check for microphone availability and maintain continuous stream
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                # Brief ambient noise calibration
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                self._mic_initialized = True
                print("[VoiceThread] Microphone initialized successfully.")

                while self._run_flag:
                    if not self.is_listening:
                        time.sleep(0.1)
                        continue

                    try:
                        self.status_changed.emit("Listening...")
                        audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=3.0)

                        if not self._run_flag or not self.is_listening:
                            continue

                        # Pass captured audio to the background recognition worker without dropping stream
                        try:
                            self._audio_queue.put_nowait((audio, time.time()))
                        except queue.Full:
                            # Drop oldest item to prevent backlog
                            try:
                                _ = self._audio_queue.get_nowait()
                            except queue.Empty:
                                pass
                            self._audio_queue.put_nowait((audio, time.time()))

                    except sr.WaitTimeoutError:
                        # Normal timeout when no speech was detected during window
                        continue
                    except Exception as e:
                        if self._run_flag:
                            print(f"[VoiceThread] Audio capture error: {e}")
                            time.sleep(0.2)

        except Exception as e:
            print(f"[VoiceThread] Failed to initialize microphone: {e}")
            self.error_occurred.emit(f"Microphone init failed: {e}")
            self.status_changed.emit("Microphone Unavailable")
            # Keep thread alive so user or system doesn't crash
            while self._run_flag:
                time.sleep(0.5)
            return

        print("[VoiceThread] Stopped.")

    def stop(self):
        """Stops the thread and cleans up background workers safely."""
        self._run_flag = False
        self.is_listening = False
        try:
            self._audio_queue.put_nowait(None)
        except Exception:
            pass
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)
        self.wait(1500)

