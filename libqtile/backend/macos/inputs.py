# Copyright (c) 2024, elParaguayo. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libqtile import config
    from libqtile.backend.macos.core import Core
    from libqtile.core.manager import Qtile


class InputManager:
    def __init__(self, qtile: Qtile, core: Core):
        self.qtile = qtile
        self.core = core
        self.keymap: dict[int, int] = {}
        self.grabbed_keys: set[tuple[int, int]] = set()

    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        mask = self.core._translate_mask(key.modifiers)
        keycode = self.keysym_from_name(key.key)  # type: ignore
        self.grabbed_keys.add((int(keycode), mask))
        return (int(keycode), mask)

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        mask = self.core._translate_mask(key.modifiers)
        keycode = self.keysym_from_name(key.key)  # type: ignore
        self.grabbed_keys.discard((int(keycode), mask))
        return (int(keycode), mask)

    def ungrab_keys(self) -> None:
        self.grabbed_keys.clear()

    def process_key_release(self, mask: int, keycode: int) -> None:
        """Called on kCGEventKeyUp; qtile key-chord machinery can hook here if needed."""

    def process_key_event(self, mask: int, keycode: int) -> bool:
        if (keycode, mask) in self.grabbed_keys:
            self.qtile.call_soon_threadsafe(self.qtile.process_key_event, keycode, mask)
            return True
        return False

    def keysym_from_name(self, name: str) -> int:
        mapping = {
            "a": 0,
            "s": 1,
            "d": 2,
            "f": 3,
            "h": 4,
            "g": 5,
            "z": 6,
            "x": 7,
            "c": 8,
            "v": 9,
            "b": 11,
            "q": 12,
            "w": 13,
            "e": 14,
            "r": 15,
            "y": 16,
            "t": 17,
            "1": 18,
            "2": 19,
            "3": 20,
            "4": 21,
            "6": 22,
            "5": 23,
            "=": 24,
            "9": 25,
            "7": 26,
            "-": 27,
            "8": 28,
            "0": 29,
            "]": 30,
            "o": 31,
            "u": 32,
            "[": 33,
            "i": 34,
            "p": 35,
            "return": 36,
            "l": 37,
            "j": 38,
            "'": 39,
            "k": 40,
            ";": 41,
            "\\": 42,
            ",": 43,
            "/": 44,
            "n": 45,
            "m": 46,
            ".": 47,
            "tab": 48,
            "space": 49,
            "`": 50,
            "delete": 51,
            "enter": 76,
            "escape": 53,
            "command": 55,
            "shift": 56,
            "capslock": 57,
            "option": 58,
            "control": 59,
            "rightshift": 60,
            "rightoption": 61,
            "rightcontrol": 62,
            "f17": 64,
            "volumeup": 72,
            "volumedown": 73,
            "mute": 74,
            "f18": 79,
            "f19": 80,
            "f20": 90,
            "f5": 96,
            "f6": 97,
            "f7": 98,
            "f3": 99,
            "f8": 100,
            "f9": 101,
            "f11": 103,
            "f13": 105,
            "f16": 106,
            "f14": 107,
            "f10": 109,
            "f12": 111,
            "f15": 113,
            "help": 114,
            "home": 115,
            "pageup": 116,
            "forwarddelete": 117,
            "f4": 118,
            "end": 119,
            "f2": 120,
            "pagedown": 121,
            "f1": 122,
            "left": 123,
            "right": 124,
            "down": 125,
            "up": 126,
            # Numpad keys
            "kp_decimal": 65,
            "kp_multiply": 67,
            "kp_add": 69,
            "num_lock": 71,
            "kp_divide": 75,
            "kp_enter": 76,
            "kp_subtract": 78,
            "kp_equal": 81,
            "kp_0": 82,
            "kp_1": 83,
            "kp_2": 84,
            "kp_3": 85,
            "kp_4": 86,
            "kp_5": 87,
            "kp_6": 88,
            "kp_7": 89,
            "kp_8": 91,
            "kp_9": 92,
            # Standard keys missing from macOS hardware — mapped to closest equivalents or sentinel
            # "insert" aliases the macOS Help key (kVK_Help = 114, already present as "help")
            "insert": 114,
            # scroll_lock, pause, print have no hardware equivalent on Apple keyboards;
            # map to F-key VKCs that are commonly remapped in system preferences as sentinels.
            "scroll_lock": 107,  # kVK_F14 — conventional macOS scroll-lock substitute
            "pause": 113,  # kVK_F15 — conventional macOS pause substitute
            "print": 105,  # kVK_F13 — conventional macOS print-screen substitute
        }
        return mapping.get(name.lower(), 0)
