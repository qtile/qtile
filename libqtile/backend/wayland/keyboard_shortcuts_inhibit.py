"""
Keyboard Shortcuts Inhibit Manager for Wayland backend.

This module manages keyboard shortcuts inhibitors, which allow applications
(such as remote desktop software or VMs) to request exclusive keyboard input,
preventing the compositor from intercepting global shortcuts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile.log_utils import logger

try:
    from libqtile.backend.wayland._ffi import ffi
except ModuleNotFoundError:
    from libqtile.backend.wayland.ffi_stub import ffi

if TYPE_CHECKING:
    from libqtile.backend.wayland.core import Core


class KeyboardShortcutsInhibitor:
    """Represents an active keyboard shortcuts inhibitor."""

    def __init__(self, handle: ffi.CData, surface: ffi.CData):
        self.handle = handle
        self.surface = surface

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeyboardShortcutsInhibitor):
            return NotImplemented
        return self.handle == other.handle

    def __hash__(self) -> int:
        return hash(id(self.handle))


class KeyboardShortcutsInhibitorManager:
    """
    Manages keyboard shortcuts inhibitors.

    This class tracks active inhibitors and provides the interface between
    the C backend and Python. The actual inhibition check happens in the C
    layer (keyboard.c) for efficiency.
    """

    def __init__(self, core: Core):
        self.core = core
        self.inhibitors: list[KeyboardShortcutsInhibitor] = []

    def add_inhibitor(self, handle: ffi.CData, surface: ffi.CData) -> bool:
        """Add a new keyboard shortcuts inhibitor."""
        inhibitor = KeyboardShortcutsInhibitor(handle, surface)
        if inhibitor not in self.inhibitors:
            self.inhibitors.append(inhibitor)
            logger.debug("Keyboard shortcuts inhibitor added (total: %d)", len(self.inhibitors))
            return True
        return False

    def remove_inhibitor(self, handle: ffi.CData) -> bool:
        """Remove a keyboard shortcuts inhibitor by its handle."""
        for i, inhibitor in enumerate(self.inhibitors):
            if inhibitor.handle == handle:
                self.inhibitors.pop(i)
                logger.debug(
                    "Keyboard shortcuts inhibitor removed (total: %d)", len(self.inhibitors)
                )
                return True
        logger.warning("Tried to remove non-existent keyboard shortcuts inhibitor")
        return False

    @property
    def has_active_inhibitors(self) -> bool:
        """Check if there are any active inhibitors."""
        return len(self.inhibitors) > 0
