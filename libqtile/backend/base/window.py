from __future__ import annotations

import enum
import typing
from abc import ABCMeta, abstractmethod

from libqtile.command.base import CommandError, CommandObject, expose_command

if typing.TYPE_CHECKING:
    from typing import Any

    from libqtile import config
    from libqtile.backend.base import Drawer
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorsType


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
        self.reserved_space: tuple[int, int, int, int] | None = None
        # Window.static sets this in case it is hooked to client_new to stop the
        # Window object from being managed, now that a Static is being used instead
        self.defunct: bool = False
        self._can_steal_focus: bool = True

        self.base_x: int | None = None
        self.base_y: int | None = None
        self.base_width: int | None = None
        self.base_height: int | None = None

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

    @expose_command()
    def is_visible(self) -> bool:
        """Is this window visible (i.e. not hidden)?"""
        return False

    @abstractmethod
    @expose_command()
    def kill(self) -> None:
        """Kill the window"""

    def get_wm_class(self) -> list | None:
        """Return the class(es) of the window"""
        return None

    def get_wm_type(self) -> str | None:
        """Return the type of the window"""
        return None

    def get_wm_role(self) -> str | None:
        """Return the role of the window"""
        return None

    @property
    def can_steal_focus(self) -> bool:
        """Is it OK for this window to steal focus?"""
        return self._can_steal_focus

    @can_steal_focus.setter
    def can_steal_focus(self, can_steal_focus: bool) -> None:
        """Can_steal_focus setter."""
        self._can_steal_focus = can_steal_focus

    def has_fixed_ratio(self) -> bool:
        """Does this window want a fixed aspect ratio?"""
        return False

    def has_fixed_size(self) -> bool:
        """Does this window want a fixed size?"""
        return False

    @property
    def urgent(self):
        """Whether this window urgently wants focus"""
        return False

    @property
    def opacity(self) -> float:
        """The opacity of this window from 0 (transparent) to 1 (opaque)."""
        return self._opacity

    @opacity.setter
    def opacity(self, opacity: float) -> None:
        """Opacity setter."""
        self._opacity = opacity

    @abstractmethod
    @expose_command()
    def place(
        self,
        x,
        y,
        width,
        height,
        borderwidth,
        bordercolor,
        above=False,
        margin=None,
        respect_hints=False,
    ):
        """Place the window in the given position."""

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None

    def _save_geometry(self):
        """Save current window geometry."""
        self.base_x = self.x
        self.base_y = self.y
        self.base_width = self.width
        self.base_height = self.height

    def _restore_geometry(self):
        """Restore previously saved window geometry."""
        if self.base_x is not None:
            self.x = self.base_x
        if self.base_y is not None:
            self.y = self.base_y
        if self.base_width is not None:
            self.width = self.base_width
        if self.base_height is not None:
            self.height = self.base_height

    @abstractmethod
    @expose_command()
    def info(self) -> dict[str, Any]:
        """
        Return information on this window.

        Mimimum required keys are:
        - name
        - x
        - y
        - width
        - height
        - group
        - id
        - wm_class

        """
        return {}

    @expose_command()
    def keep_above(self, enable: bool | None = None):
        """Keep this window above all others"""

    @expose_command()
    def keep_below(self, enable: bool | None = None):
        """Keep this window below all others"""

    @expose_command()
    def move_up(self, force: bool = False) -> None:
        """
        Move this window above the next window along the z axis.

        Will not raise a "normal" window (i.e. one that is not "kept_above/below")
        above a window that is marked as "kept_above".

        Will not raise a window where "keep_below" is True unless
        force is set to True.
        """

    @expose_command()
    def move_down(self, force: bool = False) -> None:
        """
        Move this window below the previous window along the z axis.

        Will not lower a "normal" window (i.e. one that is not "kept_above/below")
        below a window that is marked as "kept_below".

        Will not lower a window where "keep_above" is True unless
        force is set to True.
        """

    @expose_command()
    def move_to_top(self) -> None:
        """
        Move this window above all windows in the current layer
        e.g. if you have 3 windows all with "keep_above" set, calling
        this method will move the window to the top of those three windows.

        Calling this on a "normal" window will not raise it above a "kept_above"
        window.
        """

    @expose_command()
    def move_to_bottom(self) -> None:
        """
        Move this window below all windows in the current layer
        e.g. if you have 3 windows all with "keep_above" set, calling
        this method will move the window to the bottom of those three windows.

        Calling this on a "normal" window will not raise it below a "kept_below"
        window.
        """

    @abstractmethod
    @expose_command()
    def bring_to_front(self) -> None:
        """
        Bring the window to the front.

        In X11, `bring_to_front` ignores all other layering rules and brings the
        window to the very front. When that window loses focus, it will be stacked
        again according the appropriate rules.
        """


class Window(_Window, metaclass=ABCMeta):
    """
    A regular Window belonging to a client.

    Abstract methods are required to be defined as part of a specific backend's
    implementation. Non-abstract methods have default implementations here to be shared
    across backends.
    """

    qtile: Qtile

    # If float_x or float_y are None, the window has never floated
    float_x: int | None
    float_y: int | None

    def __repr__(self):
        return "%s(name=%r, wid=%i)" % (self.__class__.__name__, self.name, self.wid)

    @property
    @abstractmethod
    def group(self) -> _Group | None:
        """The group to which this window belongs."""

    @group.setter
    def group(self, group: _Group | None) -> None:
        """Set the group."""

    @property
    def floating(self) -> bool:
        """Whether this window is floating."""
        return False

    @floating.setter
    def floating(self, do_float: bool) -> None:
        raise NotImplementedError

    @property
    def maximized(self) -> bool:
        """Whether this window is maximized."""
        return False

    @maximized.setter
    def maximized(self, do_maximize: bool) -> None:
        raise NotImplementedError

    @property
    def minimized(self) -> bool:
        """Whether this window is minimized."""
        return False

    @minimized.setter
    def minimized(self, do_minimize: bool) -> None:
        raise NotImplementedError

    @property
    def fullscreen(self) -> bool:
        """Whether this window is fullscreened."""
        return False

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        raise NotImplementedError

    @property
    def wants_to_fullscreen(self) -> bool:
        """Does this window want to be fullscreen?"""
        return False

    def match(self, match: config._Match) -> bool:
        """Compare this window against a Match instance."""
        return match.compare(self)

    @abstractmethod
    @expose_command()
    def focus(self, warp: bool = True) -> None:
        """Focus this window and optional warp the pointer to it."""

    @property
    def has_focus(self):
        return self == self.qtile.current_window

    def has_user_set_position(self) -> bool:
        """Whether this window has user-defined geometry"""
        return False

    def is_transient_for(self) -> WindowType | None:
        """What window is this window a transient window for?"""
        return None

    @abstractmethod
    def get_pid(self) -> int:
        """Return the PID that owns the window."""

    def paint_borders(self, color: ColorsType, width: int) -> None:
        """Paint the window borders with the given color(s) and width"""

    @abstractmethod
    @expose_command()
    def get_position(self) -> tuple[int, int]:
        """Get the (x, y) of the window"""

    @abstractmethod
    @expose_command()
    def get_size(self) -> tuple[int, int]:
        """Get the (width, height) of the window"""

    @abstractmethod
    @expose_command()
    def move_floating(self, dx: int, dy: int) -> None:
        """Move window by dx and dy"""

    @abstractmethod
    @expose_command()
    def resize_floating(self, dw: int, dh: int) -> None:
        """Add dw and dh to size of window"""

    @abstractmethod
    @expose_command()
    def set_position_floating(self, x: int, y: int) -> None:
        """Move window to x and y"""

    @abstractmethod
    @expose_command()
    def set_position(self, x: int, y: int) -> None:
        """
        Move floating window to x and y; swap tiling window with the window under the
        pointer.
        """

    @abstractmethod
    @expose_command()
    def set_size_floating(self, w: int, h: int) -> None:
        """Set window dimensions to w and h"""

    @abstractmethod
    @expose_command()
    def toggle_floating(self) -> None:
        """Toggle the floating state of the window."""

    @abstractmethod
    @expose_command()
    def enable_floating(self) -> None:
        """Float the window."""

    @abstractmethod
    @expose_command()
    def disable_floating(self) -> None:
        """Tile the window."""

    @abstractmethod
    @expose_command()
    def toggle_maximize(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    @expose_command()
    def toggle_minimize(self) -> None:
        """Toggle the minimized state of the window."""

    @abstractmethod
    @expose_command()
    def toggle_fullscreen(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    @expose_command()
    def enable_fullscreen(self) -> None:
        """Fullscreen the window"""

    @abstractmethod
    @expose_command()
    def disable_fullscreen(self) -> None:
        """Un-fullscreen the window"""

    @abstractmethod
    @expose_command()
    def togroup(
        self,
        group_name: str | None = None,
        switch_group: bool = False,
        toggle: bool = False,
    ) -> None:
        """Move window to a specified group

        Also switch to that group if `switch_group` is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.

        Examples
        ========

        Move window to current group::

            togroup()

        Move window to group "a"::

            togroup("a")

        Move window to group "a", and switch to group "a"::

            togroup("a", switch_group=True)
        """
        self.togroup(group_name, switch_group=switch_group, toggle=toggle)

    @expose_command()
    def toscreen(self, index: int | None = None) -> None:
        """Move window to a specified screen.

        If index is not specified, we assume the current screen

        Examples
        ========

        Move window to current screen::

            toscreen()

        Move window to screen 0::

            toscreen(0)
        """
        if index is None:
            screen = self.qtile.current_screen
        else:
            try:
                screen = self.qtile.screens[index]
            except IndexError:
                raise CommandError("No such screen: %d" % index)
        self.togroup(screen.group.name)

    @expose_command()
    def set_opacity(self, opacity: float) -> None:
        """Set the window's opacity"""
        if opacity < 0.1:
            self.opacity = 0.1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    @expose_command()
    def down_opacity(self) -> None:
        """Decrease the window's opacity by 10%."""
        self.set_opacity(self.opacity - 0.1)

    @expose_command()
    def up_opacity(self) -> None:
        """Increase the window's opacity by 10%."""
        self.set_opacity(self.opacity + 0.1)

    @abstractmethod
    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Makes this window a static window, attached to a Screen.

        Values left unspecified are taken from the existing window state.
        """
        self.defunct = True

    @expose_command()
    def center(self) -> None:
        """Centers a floating window on the screen."""
        if not self.floating:
            return

        if not (self.group and self.group.screen):
            return

        screen = self.group.screen

        x = screen.x + (screen.width - self.width) // 2
        y = screen.y + (screen.height - self.height) // 2

        self.place(
            x,
            y,
            self.width,
            self.height,
            self.borderwidth,
            self.bordercolor,
            above=True,
            respect_hints=True,
        )


class Internal(_Window, metaclass=ABCMeta):
    """An Internal window belonging to Qtile."""

    def __repr__(self):
        return f"Internal(wid={self.wid})"

    @abstractmethod
    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""

    def process_window_expose(self) -> None:
        """Respond to the window being exposed. Required by X11 backend."""

    def process_button_click(self, x: int, y: int, button: int) -> None:
        """Handle a pointer button click."""

    def process_button_release(self, x: int, y: int, button: int) -> None:
        """Handle a pointer button release."""

    def process_pointer_enter(self, x: int, y: int) -> None:
        """Handle the pointer entering the window."""

    def process_pointer_leave(self, x: int, y: int) -> None:
        """Handle the pointer leaving the window."""

    def process_pointer_motion(self, x: int, y: int) -> None:
        """Handle pointer motion within the window."""

    def process_key_press(self, keycode: int) -> None:
        """Handle a key press."""


class Static(_Window, metaclass=ABCMeta):
    """A window bound to a screen rather than a group."""

    screen: config.Screen
    x: Any
    y: Any
    width: Any
    height: Any

    def __repr__(self):
        return "%s(name=%r, wid=%i)" % (self.__class__.__name__, self.name, self.wid)

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        return dict(
            name=self.name,
            wm_class=self.get_wm_class(),
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )


WindowType = Window | Internal | Static
