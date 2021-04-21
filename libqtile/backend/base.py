from __future__ import annotations

import contextlib
import enum
import typing
from abc import ABCMeta, abstractmethod

if typing.TYPE_CHECKING:
    from typing import Dict, List, Tuple, Union

    from libqtile import config
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group


class Core(metaclass=ABCMeta):
    @abstractmethod
    def finalize(self):
        """Destructor/Clean up resources"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def setup_listener(self, qtile: Qtile) -> None:
        """Setup a listener for the given qtile instance"""

    @abstractmethod
    def remove_listener(self) -> None:
        """Setup a listener for the given qtile instance"""

    @abstractmethod
    def update_desktops(self, groups, index: int) -> None:
        """Set the current desktops of the window manager"""

    @abstractmethod
    def get_screen_info(self) -> List[Tuple[int, int, int, int]]:
        """Get the screen information"""

    @abstractmethod
    def grab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Configure the backend to grab the key event"""

    @abstractmethod
    def ungrab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Release the given key event"""

    @abstractmethod
    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""

    @abstractmethod
    def grab_button(self, mouse: config.Mouse) -> int:
        """Configure the backend to grab the mouse event"""

    @abstractmethod
    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""

    @abstractmethod
    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    @abstractmethod
    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""

    def scan(self) -> None:
        """Scan for clients if required."""

    def warp_pointer(self, x: int, y: int) -> None:
        """Warp the pointer to the given coordinates relative."""

    def update_client_list(self, windows_map: Dict[int, WindowType]) -> None:
        """Update the list of windows being managed"""

    @contextlib.contextmanager
    def masked(self):
        """A context manager to suppress window events while operating on many windows."""
        yield


@enum.unique
class FloatStates(enum.Enum):
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6


class Window(metaclass=ABCMeta):
    def __init__(self):
        self.borderwidth: int = 0
        self.name: str = "<no name>"
        self.reserved_space: List = None
        self.defunct: bool = False

    @property
    @abstractmethod
    def wid(self) -> int:
        """The unique window ID"""

    @property
    @abstractmethod
    def group(self) -> _Group:
        """The group to which this window belongs."""

    @abstractmethod
    def hide(self) -> None:
        """Hide the window"""

    @abstractmethod
    def unhide(self) -> None:
        """Unhide the window"""

    @abstractmethod
    def kill(self) -> None:
        """Kill the window"""

    @property
    def can_steal_focus(self):
        """Is it OK for this window to steal focus?"""
        return True

    @property
    def floating(self) -> bool:
        """Whether this window should be floating."""
        return False

    @property
    def wants_to_fullscreen(self):
        """Does this window want to be fullscreen?"""
        return False

    def match(self, match: config.Match) -> bool:
        """Match window against given attributes."""
        return False

    @abstractmethod
    def focus(self, warp: bool):
        """Focus this window and optional warp the pointer to it."""

    @property
    def has_focus(self):
        return self == self.qtile.current_window

    @abstractmethod
    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None):
        """Place the window in the given position."""


class Internal(Window, metaclass=ABCMeta):
    pass


class Static(Window, metaclass=ABCMeta):
    pass


WindowType = typing.Union[Window, Internal, Static]
