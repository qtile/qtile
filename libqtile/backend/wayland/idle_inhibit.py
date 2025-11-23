from __future__ import annotations

from enum import IntEnum, auto
from typing import TYPE_CHECKING

from libqtile import hook
from libqtile.log_utils import logger

try:
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    from libqtile.backend.wayland.ffi_stub import ffi, lib

if TYPE_CHECKING:
    from libqtile.backend.base.window import Window
    from libqtile.core.manager import Qtile


class InhibitorType(IntEnum):
    GLOBAL = auto()
    OPEN = auto()
    APPLICATION = auto()
    VISIBLE = auto()
    FOCUS = auto()
    FULLSCREEN = auto()


inhibitor_map = {
    "open": InhibitorType.OPEN,
    "visible": InhibitorType.VISIBLE,
    "focus": InhibitorType.FOCUS,
    "fullscreen": InhibitorType.FULLSCREEN
}


class Inhibitor:
    def __init__(self, qtile: Qtile = None, window: Window | None = None, handle: ffi.CData | None = None, inhibitor_type: InhibitorType | None = None, is_layer_surface: bool = False, is_session_lock: bool = False):
        if inhibitor_type != InhibitorType.GLOBAL and ((window is None and handle is None) or inhibitor_type is None):
            raise ValueError("Inhibitor created with invalid arguments.")

        self.qtile = qtile
        self.window = window
        self.handle = handle
        self.inhibitor_type = inhibitor_type
        self.is_layer_surface = is_layer_surface
        self.is_session_lock = is_session_lock

    def check(self) -> bool:
        # If a session lock is active we only allow inhibitors from the session lock
        if self.qtile.locked:
            return self.is_session_lock and lib.qw_server_inhibitor_surface_visible(self.handle, ffi.NULL)

        match self.inhibitor_type:
            # Global inhibitor is always active
            case InhibitorType.GLOBAL:
                active = True
            # Application-set inhibitors should apply when the client is visible
            case InhibitorType.APPLICATION:
                if self.window is not None:
                    active = self.window.visible
                elif (self.is_session_lock or self.is_layer_surface):
                    active = lib.qw_server_inhibitor_surface_visible(self.handle, ffi.NULL)
                # We shouldn't really get here but, if we do, treat it as active
                else:
                    active = True
            # Inhibitor is removed when client is killed so if it exists in the list then the client
            # must be open
            case InhibitorType.OPEN:
                active = True
            case InhibitorType.FOCUS:
                active = self.qtile.current_window and self.qtile.current_window == self.window
            case InhibitorType.FULLSCREEN:
                active = self.window and self.window.fullscreen
            case InhibitorType.VISIBLE:
                active = self.window and self.window.visible
            # Ignore invalid inhibitors (there shouldn't be any though...)
            case _:
                active = False

        return active

    def __eq__(self, other):
        if not isinstance(other, Inhibitor):
            raise NotImplementedError

        return (self.window, self.handle, self.inhibitor_type, self.is_layer_surface, self.is_session_lock) == (other.window, other.handle, other.inhibitor_type, other.is_layer_surface, other.is_session_lock)

    def __repr__(self):
        name = self.window.name if self.window else "no window"
        mode = self.inhibitor_type.name.lower()
        active = "ACTIVE" if self.check() else "INACTIVE"
        return f"<window=[{name}] type=[{mode}] status=[{active}]>"


class InhibitorManager:
    def __init__(self, core):
        self.core = core
        self.inhibitors = []
        hook.subscribe.focus_change(self.check)

    def sort(self):
        self.inhibitors.sort(key=lambda x: x.inhibitor_type)

    def add_inhibitor_safe(self, inhibitor):
        if inhibitor not in self.inhibitors:
            self.inhibitors.append(inhibitor)
            self.sort()
            self.check()
            return True

        return False

    def remove_inhibitor(self, keep):
        old = len(self.inhibitors)
        self.inhibitors = [o for o in self.inhibitors if keep(o)]
        removed = len(self.inhibitors) < old
        if removed:
            self.check()

        return removed

    def add_window_inhibitor(self, window, inhibitor_type):
        itype = inhibitor_map.get(inhibitor_type)
        if itype is None:
            logger.error("Unexpected inhibitor type {inhibitor_type}.")
            return

        inhibitor = Inhibitor(qtile=self.core.qtile, window=window, inhibitor_type=itype)
        self.add_inhibitor_safe(inhibitor)

    def remove_window_inhibitor(self, window):
        self.remove_inhibitor(lambda o: o.window != window)

    def remove_window_inhibitor_by_wid(self, wid):
        def match_window_by_wid(inhibitor):
            win = inhibitor.qtile.windows_map.get(wid)
            if not win:
                return False
            return win.wid == wid

        self.remove_inhibitor(lambda o: not match_window_by_wid(o))

    def add_extension_inhibitor(self, handle, window, is_layer_surface, is_session_lock):
        inhibitor = Inhibitor(qtile=self.core.qtile, window=window, handle=handle, inhibitor_type=InhibitorType.APPLICATION)
        return self.add_inhibitor_safe(inhibitor)

    def remove_extension_inhibitor(self, pointer):
        return self.remove_inhibitor(lambda o: o.handle != pointer)

    def add_global_inhibitor(self):
        inhibitor = Inhibitor(qtile=self.core.qtile, inhibitor_type=InhibitorType.GLOBAL)
        self.add_inhibitor_safe(inhibitor)

    def remove_global_inhibitor(self):
        self.remove_inhibitor(lambda o: o.inhibitor_type != InhibitorType.GLOBAL)

    def check(self):
        inhibited = any(o.check() for o in self.inhibitors)
        self.core.set_inhibited(inhibited)
