from __future__ import annotations

from enum import IntEnum, auto
from typing import TYPE_CHECKING, Generic, TypeVar

from libqtile import hook
from libqtile.backend.base.window import Window
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from libqtile.backend.base.core import Core
    from libqtile.backend.base.window import Window
    from libqtile.core.manager import Qtile


class InhibitorType(IntEnum):
    GLOBAL = auto()
    OPEN = auto()
    APPLICATION = auto()
    VISIBLE = auto()
    FOCUS = auto()
    FULLSCREEN = auto()
    FUNCTION = auto()
    UNSET = auto()


inhibitor_map = {
    "open": InhibitorType.OPEN,
    "visible": InhibitorType.VISIBLE,
    "focus": InhibitorType.FOCUS,
    "fullscreen": InhibitorType.FULLSCREEN,
    "function": InhibitorType.FUNCTION,
}


class Inhibitor:
    def __init__(
        self,
        qtile: Qtile,
        window: Window | None = None,
        function: Callable | None = None,
        inhibitor_type: InhibitorType = InhibitorType.UNSET,
    ):
        if (
            inhibitor_type
            not in (InhibitorType.GLOBAL, InhibitorType.APPLICATION, InhibitorType.FUNCTION)
            and window is None
        ):
            raise ValueError("Inhibitor created with invalid arguments.")

        self.qtile = qtile
        self.window = window
        self.function = function
        self.inhibitor_type = inhibitor_type

    def check(self) -> bool:
        active = False

        match self.inhibitor_type:
            # Global inhibitor is always active
            case InhibitorType.GLOBAL:
                active = True
            # Inhibitor is removed when client is killed so if it exists in the list then the client
            # must be open
            case InhibitorType.OPEN:
                active = True
            case InhibitorType.FOCUS:
                active = bool(
                    self.qtile.current_window and self.qtile.current_window == self.window
                )
            case InhibitorType.FULLSCREEN:
                active = bool(self.window and self.window.fullscreen)
            case InhibitorType.VISIBLE:
                active = bool(self.window and self.window.visible)
            case InhibitorType.FUNCTION:
                if callable(self.function):
                    try:
                        active = self.function(self.qtile)
                    except Exception:
                        logger.exception("Error in idle inhibitor function.")

        return active

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Inhibitor):
            raise NotImplementedError

        return (self.window, self.function, self.inhibitor_type) == (
            other.window,
            other.function,
            other.inhibitor_type,
        )

    def __repr__(self) -> str:
        name = self.window.name if self.window else "no window"
        mode = self.inhibitor_type.name.lower()
        active = "ACTIVE" if self.check() else "inactive"
        return f"<window={name} type={mode} status={active}>"


TInhibitor = TypeVar("TInhibitor", bound=Inhibitor)


class IdleInhibitorManager(Generic[TInhibitor]):
    def __init__(self, core: Core) -> None:
        self.core = core
        self.inhibitors: list[TInhibitor] = []

    def _convert_inhibitor(self, inhibitor: Inhibitor) -> TInhibitor:
        """
        Convert a base Inhibitor into the manager's concrete inhibitor type.
        Base implementation only works if TInhibitor *is* Inhibitor.
        """
        return inhibitor  # type: ignore[return-value]

    def set_hooks(self) -> None:
        hook.subscribe.focus_change(self.check)
        hook.subscribe.startup(self.update_user_inhibitors)

    def sort(self) -> None:
        self.inhibitors.sort(key=lambda x: x.inhibitor_type)

    def add_inhibitor_safe(self, inhibitor: TInhibitor) -> bool:
        if inhibitor not in self.inhibitors:
            self.inhibitors.append(inhibitor)
            self.sort()
            self.check()
            return True

        return False

    def remove_inhibitor(
        self, remove: Callable[[TInhibitor], bool], skip_check: bool = False
    ) -> bool:
        old = len(self.inhibitors)
        self.inhibitors = [o for o in self.inhibitors if not remove(o)]
        removed = len(self.inhibitors) < old
        if removed and not skip_check:
            self.check()

        return removed

    def add_window_inhibitor(self, window: Window, inhibitor_type: str) -> None:
        itype = inhibitor_map.get(inhibitor_type)
        if itype is None:
            logger.error("Unexpected inhibitor type {inhibitor_type}.")
            return

        inhibitor = Inhibitor(qtile=self.core.qtile, window=window, inhibitor_type=itype)
        self.add_inhibitor_safe(self._convert_inhibitor(inhibitor))

    def remove_window_inhibitor(self, window: Window) -> None:
        self.remove_inhibitor(lambda o: o.window == window)

    def add_global_inhibitor(self) -> None:
        inhibitor = Inhibitor(qtile=self.core.qtile, inhibitor_type=InhibitorType.GLOBAL)
        self.add_inhibitor_safe(self._convert_inhibitor(inhibitor))

    def remove_global_inhibitor(self) -> None:
        self.remove_inhibitor(lambda o: o.inhibitor_type == InhibitorType.GLOBAL)

    def add_function_inhibitor(self, function: Callable) -> None:
        inhibitor = Inhibitor(
            qtile=self.core.qtile, function=function, inhibitor_type=InhibitorType.FUNCTION
        )
        converted = self._convert_inhibitor(inhibitor)
        self.add_inhibitor_safe(converted)

    def check(self) -> None:
        inhibited = any(o.check() for o in self.inhibitors)
        self.core.inhibited = inhibited

    def load_function_inhibitors(self) -> None:
        for inhibitor in self.core.qtile.config.idle_inhibitors:
            if inhibitor.function is not None:
                self.add_function_inhibitor(inhibitor.function)

    def update_user_inhibitors(self) -> None:
        self.remove_inhibitor(
            lambda o: o.inhibitor_type != InhibitorType.APPLICATION, skip_check=True
        )
        for win in self.core.qtile.windows_map.values():
            if isinstance(win, Window):
                win.add_config_inhibitors()

        self.load_function_inhibitors()
