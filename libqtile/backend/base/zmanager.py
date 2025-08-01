# Copyright (c) 2025 elParaguayo
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
from abc import abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from functools import wraps

from libqtile.backend.base.window import _Window


class LayerGroup(IntEnum):
    BACKGROUND = 0
    BOTTOM = 1
    KEEP_BELOW = 2
    LAYOUT = 3
    KEEP_ABOVE = 4
    MAX = 5
    FULLSCREEN = 6
    BRING_TO_FRONT = 7
    TOP = 8
    OVERLAY = 9
    SYSTEM = 10


def check_window(func):
    """
    Decorator that requires window to be stacked before proceeding.

    The decorated method must take the window's id as the first argument.
    """

    @wraps(func)
    def _wrapper(self, window, *args, **kwargs):
        if not self.is_stacked(window):
            return
        return func(self, window, *args, **kwargs)

    return _wrapper


class ZManager:
    """
    Base class for maintaining and manipulating information regarding the
    window stack.
    """

    def __init__(self, core) -> None:
        self.core = core

    @abstractmethod
    def is_stacked(self, window: _Window) -> bool:
        """Check if window is currently in the stack."""

    @abstractmethod
    def add_window(
        self, window: _Window, layer: LayerGroup = LayerGroup.LAYOUT, position="top"
    ) -> None:
        """
        Add window to the stack.

        Window can request specific layer group and be placed at "top" or "bottom" of
        the group.
        """

    @abstractmethod
    def remove_window(self, window) -> None:
        """Remove window from stack information."""

    @abstractmethod
    def move_up(self, window) -> None:
        """Move window up in the stack (in its layer group)."""

    @abstractmethod
    def move_down(self, window) -> None:
        """Move window down in the stack (in its layer group)."""

    @abstractmethod
    def move_to_top(self, window) -> None:
        """Move window to top of stack (in its layer group)."""

    @abstractmethod
    def move_to_bottom(self, window) -> None:
        """Move window to bottom of stack (in its layer group)."""

    @abstractmethod
    def move_window_to_layer(self, window, new_layer, position="top") -> None:
        """Move window to a new layer group."""

    def show_stacking_order(self):
        """Dump a visualisation of the stacking order to the log."""
