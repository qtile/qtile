from __future__ import annotations

import logging
import typing

from libqtile.backend import base
from libqtile.backend.base.window import _Window as BaseWindow
from libqtile.backend.macos import _ffi  # type: ignore
from libqtile.command.base import CommandError, expose_command

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from typing import Any

    from libqtile.backend.base.window import WindowType
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorsType


class _Window(BaseWindow):
    def __init__(self, qtile: Qtile, win_struct_ptr: Any):
        BaseWindow.__init__(self)
        # TODO: macOS AX API does not support setting visual window opacity;
        # this tracks the value in Python only so opacity commands don't crash.
        self._opacity = 1.0
        self.qtile = qtile
        self._ffi = _ffi.ffi
        self._lib = _ffi.lib

        # win_struct_ptr is already retained
        self._win = win_struct_ptr
        self._ffi.gc(self._win, self._lib.mac_window_release)

        # Cache geometry; kept in sync by place() and AX move/resize notifications.
        self._x, self._y = self.get_position()
        self._width, self._height = self.get_size()

    # -------------------------------------------------------------------------
    # Geometry properties — cache backed by native AX calls via mac_window_place
    # -------------------------------------------------------------------------

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, val: int) -> None:
        self._x = val
        self._lib.mac_window_place(self._win, self._x, self._y, self._width, self._height)

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, val: int) -> None:
        self._y = val
        self._lib.mac_window_place(self._win, self._x, self._y, self._width, self._height)

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, val: int) -> None:
        self._width = val
        self._lib.mac_window_place(self._win, self._x, self._y, self._width, self._height)

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, val: int) -> None:
        self._height = val
        self._lib.mac_window_place(self._win, self._x, self._y, self._width, self._height)

    @property
    def wid(self) -> int:
        return int(self._win.wid)

    def hide(self) -> None:
        self._lib.mac_window_set_hidden(self._win, True)

    def unhide(self) -> None:
        self._lib.mac_window_set_hidden(self._win, False)

    @expose_command()
    def is_visible(self) -> bool:
        return bool(self._lib.mac_window_is_visible(self._win))

    @expose_command()
    def kill(self) -> None:
        self._lib.mac_window_kill(self._win)

    def get_wm_class(self) -> list[str] | None:
        app_name_ptr = self._lib.mac_window_get_app_name(self._win)
        bundle_id_ptr = self._lib.mac_window_get_bundle_id(self._win)

        instance: str | None = None
        klass: str | None = None

        if app_name_ptr != self._ffi.NULL:
            instance = self._ffi.string(app_name_ptr).decode()
            self._lib.free(app_name_ptr)
        if bundle_id_ptr != self._ffi.NULL:
            klass = self._ffi.string(bundle_id_ptr).decode()
            self._lib.free(bundle_id_ptr)

        if instance is None and klass is None:
            return None
        # Always return a 2-element list [instance_name, class_name] so callers
        # can safely index [0] and [1] without risk of IndexError.
        return [instance or "Unknown", klass or "Unknown"]

    def get_wm_type(self) -> str | None:
        role_ptr = self._lib.mac_window_get_role(self._win)
        if role_ptr == self._ffi.NULL:
            return None
        role = self._ffi.string(role_ptr).decode()
        self._lib.free(role_ptr)

        if role == "AXWindow":
            return "normal"
        elif role in ("AXSheet", "AXDrawer", "AXDialog"):
            return "dialog"
        elif role == "AXPanel":
            return "utility"
        return None

    def get_wm_role(self) -> str | None:
        role_ptr = self._lib.mac_window_get_role(self._win)
        if role_ptr == self._ffi.NULL:
            return None
        role = self._ffi.string(role_ptr).decode()
        self._lib.free(role_ptr)
        return role

    @expose_command()
    def get_position(self) -> tuple[int, int]:
        x = self._ffi.new("int *")
        y = self._ffi.new("int *")
        self._lib.mac_window_get_position(self._win, x, y)
        return x[0], y[0]

    @expose_command()
    def get_size(self) -> tuple[int, int]:
        w = self._ffi.new("int *")
        h = self._ffi.new("int *")
        self._lib.mac_window_get_size(self._win, w, h)
        return w[0], h[0]

    def place(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        borderwidth: int,
        bordercolor: ColorsType | None,
        above: bool = False,
        margin: int | list[int] | None = None,
        respect_hints: bool = False,
    ) -> None:
        self._lib.mac_window_place(self._win, x, y, width, height)
        self._x, self._y, self._width, self._height = x, y, width, height
        self.float_x = x
        self.float_y = y
        if above:
            self.bring_to_front()

    @expose_command()
    def bring_to_front(self) -> None:
        self._lib.mac_window_bring_to_front(self._win)

    @expose_command()
    def move_to_top(self) -> None:
        # TODO: macOS AX API has no concept of window layers; bring_to_front()
        # always raises to the top, ignoring any keep_above state.
        self.bring_to_front()


class Static(_Window, base.Static):
    def __init__(
        self,
        qtile: Qtile,
        win_struct_ptr: Any,
        screen: Any,
        x=None,
        y=None,
        width=None,
        height=None,
    ):
        _Window.__init__(self, qtile, win_struct_ptr)
        self.screen = screen
        self._x = x if x is not None else self.get_position()[0]
        self._y = y if y is not None else self.get_position()[1]
        self._width = width if width is not None else self.get_size()[0]
        self._height = height if height is not None else self.get_size()[1]
        self._lib.mac_window_place(self._win, self._x, self._y, self._width, self._height)
        name_ptr = self._lib.mac_window_get_name(self._win)
        if name_ptr != self._ffi.NULL:
            self.name = self._ffi.string(name_ptr).decode()
            self._lib.free(name_ptr)

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        self._lib.mac_window_focus(self._win)


class Window(_Window, base.Window):
    def __init__(self, qtile: Qtile, win_struct_ptr: Any):
        _Window.__init__(self, qtile, win_struct_ptr)
        self._group: _Group | None = None
        self._floating: bool = False
        self._fullscreen: bool = False
        self._maximized: bool = False
        self._minimized: bool = False
        self._urgent: bool = False

        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int | None = None
        self._float_height: int | None = None
        self.bordercolor: ColorsType | None = None
        self.borderwidth: int = 0

        # Populate name from the window title; AXTitleChanged notifications keep it current.
        name_ptr = self._lib.mac_window_get_name(self._win)
        if name_ptr != self._ffi.NULL:
            self.name = self._ffi.string(name_ptr).decode()
            self._lib.free(name_ptr)

    @property
    def floating(self) -> bool:
        return self._floating

    @floating.setter
    def floating(self, do_float: bool) -> None:
        self._floating = do_float
        if self.group:
            self.group.mark_floating(self, do_float)

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        self._lib.mac_window_set_fullscreen(self._win, do_full)
        self._fullscreen = do_full

    @property
    def maximized(self) -> bool:
        return self._maximized

    @maximized.setter
    def maximized(self, do_maximize: bool) -> None:
        self._lib.mac_window_set_maximized(self._win, do_maximize)
        self._maximized = do_maximize

    @property
    def minimized(self) -> bool:
        return self._minimized

    @minimized.setter
    def minimized(self, do_minimize: bool) -> None:
        self._lib.mac_window_set_minimized(self._win, do_minimize)
        self._minimized = do_minimize

    @property
    def group(self) -> _Group | None:
        return self._group

    @group.setter
    def group(self, group: _Group | None) -> None:
        self._group = group

    @property
    def urgent(self) -> bool:
        return self._urgent

    @urgent.setter
    def urgent(self, urgent: bool) -> None:
        # macOS has no native urgency concept equivalent to X11 WM_HINTS urgency.
        # Store the value so reads are consistent; log at debug level so callers
        # know the request was received but not forwarded to the OS.
        self._urgent = urgent
        if urgent:
            logger.debug(
                "urgent hint set on macOS window %r (no native urgency signal available)",
                self.name,
            )

    def paint_borders(self, color: ColorsType, width: int) -> None:
        # macOS windows are managed by the compositor; qtile cannot paint borders
        # on native windows via the Accessibility API.  Track the values in Python
        # so that info() reports them correctly, but no visual change is made.
        self.bordercolor = color
        self.borderwidth = width

    def is_transient_for(self) -> WindowType | None:
        """Return the parent window if this window is a sheet/transient.

        Uses kAXParentAttribute via mac_window_get_parent to find the owning
        window for sheet and drawer windows.  Returns None if no parent is found
        or if the parent is not a managed qtile window.
        """
        parent_win = self._ffi.new("struct mac_window *")
        err = self._lib.mac_window_get_parent(self._win, parent_win)
        if err != 0:
            return None
        parent_wid = int(parent_win.wid)
        if parent_wid == 0:
            return None
        return self.qtile.windows_map.get(parent_wid)

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        self._lib.mac_window_focus(self._win)
        if warp:
            x, y = self.get_position()
            w, h = self.get_size()
            self.qtile.core.warp_pointer(x + w // 2, y + h // 2)

    def get_pid(self) -> int:
        return self._lib.mac_window_get_pid(self._win)

    @expose_command()
    def info(self) -> dict[str, Any]:
        x, y = self.get_position()
        width, height = self.get_size()
        name_ptr = self._lib.mac_window_get_name(self._win)
        if name_ptr == self._ffi.NULL:
            name = "Unknown"
        else:
            name = self._ffi.string(name_ptr).decode()
            self._lib.free(name_ptr)

        return dict(
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            group=self.group.name if self.group else None,
            id=self.wid,
            wm_class=self.get_wm_class(),
            floating=self.floating,
            fullscreen=self.fullscreen,
            maximized=self.maximized,
            minimized=self.minimized,
        )

    @expose_command()
    def toggle_floating(self) -> None:
        self.floating = not self.floating

    @expose_command()
    def enable_floating(self) -> None:
        self.floating = True

    @expose_command()
    def disable_floating(self) -> None:
        self.floating = False

    @expose_command()
    def toggle_maximize(self) -> None:
        self.maximized = not self.maximized

    @expose_command()
    def toggle_minimize(self) -> None:
        self.minimized = not self.minimized

    @expose_command()
    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    @expose_command()
    def enable_fullscreen(self) -> None:
        self.fullscreen = True

    @expose_command()
    def disable_fullscreen(self) -> None:
        self.fullscreen = False

    @expose_command()
    def move_floating(self, dx: int, dy: int) -> None:
        x, y = self.get_position()
        w, h = self.get_size()
        self.place(x + dx, y + dy, w, h, self.borderwidth, self.bordercolor)

    @expose_command()
    def resize_floating(self, dw: int, dh: int) -> None:
        x, y = self.get_position()
        w, h = self.get_size()
        self.place(x, y, w + dw, h + dh, self.borderwidth, self.bordercolor)

    @expose_command()
    def set_position_floating(self, x: int, y: int) -> None:
        w, h = self.get_size()
        self.place(x, y, w, h, self.borderwidth, self.bordercolor)

    @expose_command()
    def set_position(self, x: int, y: int) -> None:
        if self.floating:
            self.set_position_floating(x, y)

    @expose_command()
    def set_size_floating(self, w: int, h: int) -> None:
        x, y = self.get_position()
        self.place(x, y, w, h, self.borderwidth, self.bordercolor)

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self.defunct = True
        if screen is None:
            scr = self.qtile.current_screen
        else:
            scr = self.qtile.screens[screen]

        # We need a retained ptr for the new Static object
        self._lib.mac_window_retain(self._win)
        s = Static(self.qtile, self._win, scr, x, y, width, height)
        self.qtile.manage(s)

    @expose_command()
    def togroup(
        self, group_name: str | None = None, switch_group: bool = False, toggle: bool = False
    ) -> None:
        if group_name is None:
            group: _Group | None = self.qtile.current_group
        else:
            group = self.qtile.groups_map.get(group_name)
            if group is None:
                raise CommandError(f"No such group: {group_name}")

        if self.group == group:
            if toggle and self.qtile.current_screen.previous_group:
                group = self.qtile.current_screen.previous_group
            else:
                return

        if self.group:
            self.group.remove(self)

        if group:
            group.add(self)
            if switch_group:
                group.toscreen()
