from __future__ import annotations

import contextlib
import enum
import typing
from abc import ABCMeta, abstractmethod

from libqtile.command.base import CommandObject, ItemT

if typing.TYPE_CHECKING:
    from typing import Dict, List, Optional, Tuple, Union

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

    @abstractmethod
    def focus_by_click(self, event: typing.Any) -> None:
        """Focus a window by clicking on it."""

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

    def flush(self) -> None:
        """If needed, flush the backend's event queue."""

    def graceful_shutdown(self):
        """Try to close windows gracefully before exiting"""

    def simulate_keypress(self, modifiers: List[str], key: str) -> None:
        """Simulate a keypress with given modifiers"""

    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal, returning success."""
        return False


@enum.unique
class FloatStates(enum.Enum):
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6


class _Window(CommandObject, metaclass=ABCMeta):
    def __init__(self):
        self.borderwidth: int = 0
        self.name: str = "<no name>"
        self.reserved_space: List = None
        self.defunct: bool = False

    @property
    @abstractmethod
    def group(self) -> _Group:
        """The group to which this window belongs."""

    @property
    @abstractmethod
    def wid(self) -> int:
        """The unique window ID"""

    @abstractmethod
    def hide(self) -> None:
        """Hide the window"""

    @abstractmethod
    def unhide(self) -> None:
        """Unhide the window"""

    @abstractmethod
    def kill(self) -> None:
        """Kill the window"""

    def get_wm_class(self) -> Optional[str]:
        """Return the class of the window"""

    @property
    def can_steal_focus(self):
        """Is it OK for this window to steal focus?"""
        return True

    @abstractmethod
    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None, respect_hints=False):
        """Place the window in the given position."""

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None


class Window(_Window, metaclass=ABCMeta):
    @property
    def floating(self) -> bool:
        """Whether this window is floating."""
        return False

    @property
    def maximized(self) -> bool:
        """Whether this window is maximized."""
        return False

    @property
    def fullscreen(self) -> bool:
        """Whether this window is fullscreened."""
        return False

    @property
    def wants_to_fullscreen(self) -> bool:
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

    def has_user_set_position(self) -> bool:
        """Whether this window has user-defined geometry"""
        return False

    def is_transient_for(self) -> Optional["WindowType"]:
        """What window is this window a transient windor for?"""
        return None

    @abstractmethod
    def get_pid(self) -> int:
        """Return the PID that owns the window."""

    def paint_borders(self, color, width) -> None:
        """Paint the window borders with the given color and width"""

    @abstractmethod
    def cmd_focus(self, warp: Optional[bool] = None) -> None:
        """Focuses the window."""

    @abstractmethod
    def cmd_info(self) -> Dict:
        """Return a dictionary of info."""

    @abstractmethod
    def cmd_get_position(self) -> Tuple[int, int]:
        """Get the (x, y) of the window"""

    @abstractmethod
    def cmd_get_size(self) -> Tuple[int, int]:
        """Get the (width, height) of the window"""

    @abstractmethod
    def cmd_move_floating(self, dx: int, dy: int) -> None:
        """Move window by dx and dy"""

    @abstractmethod
    def cmd_resize_floating(self, dw: int, dh: int) -> None:
        """Add dw and dh to size of window"""

    @abstractmethod
    def cmd_set_position_floating(self, x: int, y: int) -> None:
        """Move window to x and y"""

    @abstractmethod
    def cmd_set_size_floating(self, w: int, h: int) -> None:
        """Set window dimensions to w and h"""

    @abstractmethod
    def cmd_place(self, x, y, width, height, borderwidth, bordercolor,
                  above=False, margin=None) -> None:
        """Place the window with the given position and geometry."""

    @abstractmethod
    def cmd_toggle_floating(self) -> None:
        """Toggle the floating state of the window."""

    @abstractmethod
    def cmd_enable_floating(self) -> None:
        """Float the window."""

    @abstractmethod
    def cmd_disable_floating(self) -> None:
        """Tile the window."""

    @abstractmethod
    def cmd_toggle_maximize(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    def cmd_toggle_fullscreen(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    def cmd_enable_fullscreen(self) -> None:
        """Fullscreen the window"""

    @abstractmethod
    def cmd_disable_fullscreen(self) -> None:
        """Un-fullscreen the window"""

    @abstractmethod
    def cmd_bring_to_front(self) -> None:
        """Bring the window to the front"""

    def cmd_opacity(self, opacity):
        """Set the window's opacity"""
        if opacity < .1:
            self.opacity = .1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    def cmd_down_opacity(self):
        """Decrease the window's opacity"""
        if self.opacity > .2:
            # don't go completely clear
            self.opacity -= .1
        else:
            self.opacity = .1

    def cmd_up_opacity(self):
        """Increase the window's opacity"""
        if self.opacity < .9:
            self.opacity += .1
        else:
            self.opacity = 1

    @abstractmethod
    def cmd_kill(self) -> None:
        """Kill the window. Try to be polite."""


class Internal(_Window, metaclass=ABCMeta):
    pass


class Static(_Window, metaclass=ABCMeta):
    pass


WindowType = typing.Union[Window, Internal, Static]
