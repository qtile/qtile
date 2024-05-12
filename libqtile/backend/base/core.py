from __future__ import annotations

import contextlib
import typing
from abc import ABCMeta, abstractmethod

from libqtile.command.base import CommandObject, expose_command
from libqtile.config import ScreenRect

if typing.TYPE_CHECKING:
    from typing import Any

    from libqtile import config
    from libqtile.backend.base import Internal
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group


class Core(CommandObject, metaclass=ABCMeta):
    painter: Any
    supports_restarting: bool = True
    qtile: Qtile

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the backend"""
        pass

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None

    @abstractmethod
    def finalize(self):
        """Destructor/Clean up resources"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def setup_listener(self) -> None:
        """Setup a listener for the given qtile instance"""

    @abstractmethod
    def remove_listener(self) -> None:
        """Setup a listener for the given qtile instance"""

    def update_desktops(self, groups: list[_Group], index: int) -> None:
        """Set the current desktops of the window manager"""

    @abstractmethod
    def get_screen_info(self) -> list[ScreenRect]:
        """Get the screen information"""

    @abstractmethod
    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Configure the backend to grab the key event"""

    @abstractmethod
    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Release the given key event"""

    @abstractmethod
    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""

    @abstractmethod
    def grab_button(self, mouse: config.Mouse) -> int:
        """Configure the backend to grab the mouse event"""

    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""

    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""

    def on_config_load(self, initial: bool) -> None:
        """
        Respond to config loading. `initial` will be `True` if Qtile just started.
        """

    def warp_pointer(self, x: int, y: int) -> None:
        """Warp the pointer to the given coordinates relative."""

    @contextlib.contextmanager
    def masked(self):
        """A context manager to suppress window events while operating on many windows."""
        yield

    def create_internal(self, x: int, y: int, width: int, height: int) -> Internal:
        """Create an internal window controlled by Qtile."""
        raise NotImplementedError  # Only error when called, not when instantiating class

    def flush(self) -> None:
        """If needed, flush the backend's event queue."""

    def graceful_shutdown(self):
        """Try to close windows gracefully before exiting"""

    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        """Simulate a keypress with given modifiers"""

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        raise NotImplementedError

    def get_mouse_position(self) -> tuple[int, int]:
        """Get mouse coordinates."""
        raise NotImplementedError

    @expose_command()
    def info(self) -> dict[str, Any]:
        """Get basic information about the running backend."""
        return {"backend": self.name, "display_name": self.display_name}
