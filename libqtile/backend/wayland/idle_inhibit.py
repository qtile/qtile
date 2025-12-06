from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile.backend.base.idle_inhibit import IdleInhibitorManager as BaseIdleInhibitorManager
from libqtile.backend.base.idle_inhibit import Inhibitor, InhibitorType

try:
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    from libqtile.backend.wayland.ffi_stub import ffi, lib

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from libqtile.backend.base.window import Window
    from libqtile.core.manager import Qtile


class WaylandInhibitor(Inhibitor):
    def __init__(
        self,
        qtile: Qtile,
        window: Window | None = None,
        function: Callable | None = None,
        handle: ffi.CData | None = None,
        inhibitor_type: InhibitorType = InhibitorType.UNSET,
        is_layer_surface: bool = False,
        is_session_lock: bool = False,
    ):
        super().__init__(qtile, window, function, inhibitor_type)
        self.handle = handle
        self.is_layer_surface = is_layer_surface
        self.is_session_lock = is_session_lock

    def check(self) -> bool:
        # If a session lock is active we only allow inhibitors from the session lock
        if self.qtile.locked:
            return self.is_session_lock and lib.qw_server_inhibitor_surface_visible(
                self.handle, ffi.NULL
            )

        if self.inhibitor_type == InhibitorType.APPLICATION:
            # Application-set inhibitors should apply when the client is visible
            if self.window is not None:
                active = self.window.visible
            elif self.is_session_lock or self.is_layer_surface:
                active = lib.qw_server_inhibitor_surface_visible(self.handle, ffi.NULL)
            # We shouldn't really get here but, if we do, treat it as active
            else:
                active = True
            return active

        return super().check()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, WaylandInhibitor):
            raise NotImplementedError

        return (
            self.window,
            self.function,
            self.handle,
            self.inhibitor_type,
            self.is_layer_surface,
            self.is_session_lock,
        ) == (
            other.window,
            other.function,
            other.handle,
            other.inhibitor_type,
            other.is_layer_surface,
            other.is_session_lock,
        )

    @classmethod
    def from_base_inhibitor(cls, inhibitor: Inhibitor) -> WaylandInhibitor:
        if isinstance(inhibitor, WaylandInhibitor):
            return inhibitor
        return cls(
            qtile=inhibitor.qtile,
            window=inhibitor.window,
            function=inhibitor.function,
            inhibitor_type=inhibitor.inhibitor_type,
        )


class IdleInhibitorManager(BaseIdleInhibitorManager[WaylandInhibitor]):
    def _convert_inhibitor(self, inhibitor: Inhibitor) -> WaylandInhibitor:
        return WaylandInhibitor.from_base_inhibitor(inhibitor)

    def add_extension_inhibitor(
        self,
        handle: ffi.CData,
        window: Window | None,
        is_layer_surface: bool,
        is_session_lock: bool,
    ) -> bool:
        inhibitor = WaylandInhibitor(
            qtile=self.core.qtile,
            window=window,
            handle=handle,
            inhibitor_type=InhibitorType.APPLICATION,
            is_layer_surface=is_layer_surface,
            is_session_lock=is_session_lock,
        )
        return self.add_inhibitor_safe(inhibitor)

    def remove_extension_inhibitor(self, pointer: ffi.CData) -> bool:
        return self.remove_inhibitor(lambda o: o.handle == pointer)
