import re
import time
from typing import Optional, Tuple

class VoiceCommandRecognizer:
    """
    Rule-based parser for predefined presentation voice commands.
    Provides speech normalization, fuzzy phrase matching for common variations,
    and command cooldown/debouncing to prevent duplicate executions.
    """
    def __init__(self, cooldown_time: float = 0.5):
        self.cooldown_time = cooldown_time
        self.last_command_time = 0.0
        self.last_command = "None"

        # Predefined phrase mappings
        self._next_phrases = {
            "next slide", "next", "go to next slide", "go to the next slide",
            "go next", "next page", "slide next", "forward", "move forward",
            "next presentation slide", "advance", "advance slide", "next one",
            "show next slide", "move to next slide", "slide forward", "go forward"
        }
        self._prev_phrases = {
            "previous slide", "previous", "go to previous slide", "go to the previous slide",
            "go previous", "prev", "back", "go back", "previous page", "slide previous",
            "move back", "last slide", "last page", "prior slide", "prior",
            "previous one", "back one", "step back", "slide back", "backward",
            "backwards", "go backward", "go to last slide"
        }
        self._screenshot_phrases = {
            "take screenshot", "take a screenshot", "capture screenshot",
            "capture the screenshot", "screenshot", "screen capture",
            "capture screen", "capture the screen", "take snapshot", "snapshot",
            "snap screen", "print screen", "save screen", "screen grab", "grab screen",
            "take screen shot", "capture screen shot"
        }
        self._slideshow_start_phrases = {
            "slide show", "slideshow", "start slide show", "start slideshow",
            "start presentation", "begin slide show", "begin slideshow",
            "begin presentation", "play slide show", "play slideshow",
            "launch slideshow", "launch slide show", "launch presentation",
            "open slideshow", "open slide show", "run slideshow", "run slide show",
            "present", "start presenting", "view slideshow", "view slide show"
        }
        self._slideshow_end_phrases = {
            "exit slide show", "exit slideshow", "stop slide show", "stop slideshow",
            "end slide show", "end slideshow", "close slide show", "close slideshow",
            "exit presentation", "stop presentation", "end presentation",
            "close presentation", "quit slide show", "quit slideshow",
            "stop presenting"
        }

    WORD_TO_DIGIT = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
        "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
        "nineteenth": 19, "twentieth": 20, "thirtieth": 30, "fortieth": 40,
        "fiftieth": 50, "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
    }

    @classmethod
    def parse_number(cls, text: str) -> Optional[int]:
        """
        Parses a string representing a number (digits or English words up to 999) into an integer.
        Returns None if not a valid number.
        """
        text = text.strip().lower()
        # Direct integer check
        if text.isdigit():
            val = int(text)
            return val if val > 0 else None

        # Check for ordinal digits like '10th', '1st', '2nd', '3rd'
        m = re.match(r"^(\d+)(st|nd|rd|th)$", text)
        if m:
            val = int(m.group(1))
            return val if val > 0 else None

        # Word-based numbers
        words = text.replace("-", " ").split()
        words = [w for w in words if w != "and"]
        if not words:
            return None

        total = 0
        current = 0
        for w in words:
            if w in cls.WORD_TO_DIGIT:
                current += cls.WORD_TO_DIGIT[w]
            elif w in ("hundred", "hundredth"):
                current = max(1, current) * 100
                total += current
                current = 0
            elif w.isdigit():
                current += int(w)
            else:
                return None
        total += current
        return total if total > 0 else None

    def set_cooldown(self, seconds: float):
        """Dynamically updates the debouncing cooldown duration."""
        self.cooldown_time = max(0.1, float(seconds))

    @staticmethod
    def normalize_text(text: str) -> str:
        """Converts text to lowercase, normalizes phrases and spaces."""
        if not text:
            return ""
        # Lowercase and replace punctuation with spaces
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Normalize common STT multi-word variations and homophones
        cleaned = re.sub(r"\bscreen\s+shot\b", "screenshot", cleaned)
        cleaned = re.sub(r"\bscreenshoot\b", "screenshot", cleaned)
        cleaned = re.sub(r"\b(necks|nest)\s+slide\b", "next slide", cleaned)
        cleaned = re.sub(r"\bgot\s+to\b", "go to", cleaned)
        cleaned = re.sub(r"\bgoto\b", "go to", cleaned)
        return cleaned

    @staticmethod
    def strip_conversational_padding(text: str) -> str:
        """Strips polite leading/trailing words without losing command intent."""
        # Strip common leading conversational openers
        leading_pattern = r"^(please|can you please|could you please|can you|could you|would you|will you|hey|okay|ok|just|lets|let us)\s+"
        cleaned = re.sub(leading_pattern, "", text).strip()
        # Strip trailing polite/filler words
        trailing_pattern = r"\s+(please|now|thanks|thank you)$"
        cleaned = re.sub(trailing_pattern, "", cleaned).strip()
        return cleaned

    def parse_command(self, raw_text: str) -> Optional[str]:
        """
        Parses normalized spoken text against predefined presentation command rules.
        Ensures high accuracy on command variations while preserving high precision
        against false-triggering on natural presentation speech.
        
        Returns:
            str: 'NEXT_SLIDE', 'PREVIOUS_SLIDE', 'SCREENSHOT', 'START_SLIDESHOW',
                 'END_SLIDESHOW', 'GOTO_SLIDE:<N>', or None if no match.
        """
        normalized = self.normalize_text(raw_text)
        if not normalized:
            return None

        # 1. Exact phrase match against full normalized text
        if normalized in self._next_phrases:
            return "NEXT_SLIDE"
        if normalized in self._prev_phrases:
            return "PREVIOUS_SLIDE"
        if normalized in self._screenshot_phrases:
            return "SCREENSHOT"
        if normalized in self._slideshow_start_phrases:
            return "START_SLIDESHOW"
        if normalized in self._slideshow_end_phrases:
            return "END_SLIDESHOW"

        # 2. Check after conversational padding removal (e.g. "please go to next slide")
        unpadded = self.strip_conversational_padding(normalized)
        if unpadded in self._next_phrases:
            return "NEXT_SLIDE"
        if unpadded in self._prev_phrases:
            return "PREVIOUS_SLIDE"
        if unpadded in self._screenshot_phrases:
            return "SCREENSHOT"
        if unpadded in self._slideshow_start_phrases:
            return "START_SLIDESHOW"
        if unpadded in self._slideshow_end_phrases:
            return "END_SLIDESHOW"

        # 3. Direct Slide Navigation Rules ("go to slide 10", "slide 5", "page 3", "slide number 10", etc.)
        slide_match = re.match(
            r"^(?:(?:go\s+to|goto|jump\s+to|move\s+to|switch\s+to|show|open)\s+)?(?:the\s+)?(?:slide|page)(?:\s+number)?\s+(.+)$",
            unpadded
        )
        if slide_match:
            target = slide_match.group(1).strip()
            num = self.parse_number(target)
            if num is not None:
                return f"GOTO_SLIDE:{num}"

        # Ordinal before slide: "10th slide", "tenth slide", "go to the 10th slide"
        ordinal_match = re.match(
            r"^(?:(?:go\s+to|goto|jump\s+to|move\s+to|switch\s+to|show|open)\s+)?(?:the\s+)?(.+?)\s+(?:slide|page)$",
            unpadded
        )
        if ordinal_match:
            target = ordinal_match.group(1).strip()
            if target not in {"next", "previous", "prev", "last", "prior", "another"}:
                num = self.parse_number(target)
                if num is not None:
                    return f"GOTO_SLIDE:{num}"

        # Direct "go to 10" / "goto 10" / "jump to 10"
        goto_match = re.match(r"^(?:go\s+to|goto|jump\s+to|move\s+to)\s+(.+)$", unpadded)
        if goto_match:
            target = goto_match.group(1).strip()
            if target not in {"next", "previous", "prev", "last", "prior"}:
                num = self.parse_number(target)
                if num is not None:
                    return f"GOTO_SLIDE:{num}"

        tokens = unpadded.split()

        # Precision guard: Reject long conversational sentences (> 6 words)
        # to prevent ordinary speech during presentations from triggering actions.
        if len(tokens) > 6:
            return None

        # 4. Flexible Keyword & Pattern Rules (Filtered tokens)
        filtered_tokens = [w for w in tokens if w not in {"the", "a", "an", "to", "for"}]
        filtered_set = set(filtered_tokens)

        # Slideshow checks
        if "slideshow" in filtered_set or ("slide" in filtered_set and "show" in filtered_set):
            if any(w in filtered_set for w in ("exit", "stop", "end", "close", "quit", "leave")):
                return "END_SLIDESHOW"
            return "START_SLIDESHOW"
        if "presentation" in filtered_set:
            if any(w in filtered_set for w in ("exit", "stop", "end", "close", "quit")):
                return "END_SLIDESHOW"
            if any(w in filtered_set for w in ("start", "begin", "launch", "play", "run", "open", "present")):
                return "START_SLIDESHOW"

        # Screenshot checks
        if "screenshot" in filtered_set or "snapshot" in filtered_set:
            return "SCREENSHOT"
        if "capture" in filtered_set and "screen" in filtered_set:
            return "SCREENSHOT"
        if "screen" in filtered_set and any(w in filtered_set for w in ("shot", "grab", "snip", "save", "capture")):
            return "SCREENSHOT"
        if "print" in filtered_set and "screen" in filtered_set:
            return "SCREENSHOT"

        # Next Slide checks
        if any(w in filtered_set for w in ("next", "forward", "advance")):
            # Standalone single-word commands
            if filtered_tokens in (["next"], ["forward"], ["advance"]):
                return "NEXT_SLIDE"
            # Explicit directional commands
            if "slide" in filtered_set or "page" in filtered_set or "one" in filtered_set:
                return "NEXT_SLIDE"
            if filtered_tokens in (["go", "next"], ["move", "forward"], ["slide", "forward"], ["go", "forward"]):
                return "NEXT_SLIDE"

        # Previous Slide checks
        if any(w in filtered_set for w in ("previous", "prev", "back", "backward", "backwards", "prior", "last")):
            # Standalone single-word commands
            if filtered_tokens in (["previous"], ["prev"], ["back"], ["backward"], ["backwards"], ["prior"]):
                return "PREVIOUS_SLIDE"
            # Explicit directional commands
            if "slide" in filtered_set or "page" in filtered_set or "one" in filtered_set:
                return "PREVIOUS_SLIDE"
            if filtered_tokens in (["go", "back"], ["move", "back"], ["step", "back"], ["slide", "back"]):
                return "PREVIOUS_SLIDE"

        return None

    def recognize(self, raw_text: str) -> Tuple[Optional[str], str]:
        """
        Processes spoken text and applies debouncing/cooldown logic.
        Uses standard cooldown for repeated identical commands, and a fast-path
        cooldown when switching between different command types.
        
        Returns:
            Tuple[Optional[str], str]: (action_name, status_message)
            action_name is 'NEXT_SLIDE', 'PREVIOUS_SLIDE', 'SCREENSHOT', or None.
        """
        action = self.parse_command(raw_text)
        if not action:
            return None, "NO_MATCH"

        current_time = time.time()
        time_since_last = current_time - self.last_command_time

        # Fast-path for alternating different commands (e.g. NEXT_SLIDE -> SCREENSHOT)
        effective_cooldown = self.cooldown_time if action == self.last_command else min(0.3, self.cooldown_time)

        if time_since_last < effective_cooldown:
            # Command was recognized, but blocked by cooldown
            return None, f"COOLDOWN ({time_since_last:.1f}s < {effective_cooldown:.1f}s)"

        # Successfully triggered
        self.last_command_time = current_time
        self.last_command = action
        return action, "TRIGGERED"

    def reset_cooldown(self):
        """Resets cooldown timestamp immediately."""
        self.last_command_time = 0.0
        self.last_command = "None"

