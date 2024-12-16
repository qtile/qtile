# Copyright (c) 2021 Matt Colligan
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

from __future__ import annotations

import abc
import functools
import typing

import cairocffi
import wlroots.wlr_types.foreign_toplevel_management_v1 as ftm
from pywayland.server import Client, Listener
from wlroots import PtrHasData
from wlroots import lib as wlr_lib
from wlroots.util.box import Box
from wlroots.wlr_types import Buffer
from wlroots.wlr_types.idle_inhibit_v1 import IdleInhibitorV1
from wlroots.wlr_types.pointer_constraints_v1 import (
    PointerConstraintV1,
    PointerConstraintV1StateField,
)
from wlroots.wlr_types.scene import SceneBuffer, SceneRect, SceneTree

from libqtile import config, hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.drawer import Drawer
from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.command.base import CommandError, expose_command
from libqtile.log_utils import logger

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    pass

if typing.TYPE_CHECKING:
    from typing import Any

    from wlroots.wlr_types import Surface

    from libqtile.backend.wayland.core import Core
    from libqtile.command.base import CommandObject, ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorsType, ColorType

S = typing.TypeVar("S", bound=PtrHasData)


@functools.lru_cache
def _rgb(color: ColorType) -> ffi.CData:
    """Helper to create and cache float[4] arrays for border painting"""
    if isinstance(color, ffi.CData):
        return color
    return ffi.new("float[4]", utils.rgb(color))


class _Base:
    _wid: int

    @property
    def wid(self) -> int:
        return self._wid

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int) -> None:
        self._width = width

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, height: int) -> None:
        self._height = height


class Window(typing.Generic[S], _Base, base.Window, HasListeners):
    """
    This is a generic window class for "regular" windows. The type variable `S` denotes
    which type of surface the window manages, and by extension which shell the window
    belongs to. While this does implement some of `base.Window`'s abstract methods, the
    concrete classes are responsible for implementing a few others.
    """

    def __init__(self, core: Core, qtile: Qtile, surface: S):
        base.Window.__init__(self)
        self.core = core
        self.qtile = qtile
        self.surface = surface
        self._group: _Group | None = None
        self.x = 0
        self.y = 0
        self._opacity: float = 1.0
        self._wm_class: str | None = None
        self._idle_inhibitors_count: int = 0
        self._urgent = False

        # Create a scene-graph tree for this window and its borders
        self.data_handle: ffi.CData = ffi.new_handle(self)
        self.container = SceneTree.create(core.mid_window_tree)
        self.container.node.set_enabled(enabled=False)
        self.container.node.data = self.data_handle

        # The borders are wlr_scene_rects.
        # Inner list: N, E, S, W edges
        # Outer list: outside-in borders i.e. multiple for multiple borders
        self._borders: list[list[SceneRect]] = []
        self.bordercolor: ColorsType = "000000"

        # This is a placeholder to be set properly when the window maps for the first
        # time (and therefore exposed to the user). We need the attribute to exist so
        # that __repr__ doesn't AttributeError.
        self._wid: int = -1

        self._width: int = 0
        self._height: int = 0
        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int = 0
        self._float_height: int = 0
        self._float_state = FloatStates.NOT_FLOATING

        # Each regular window gets a foreign toplevel handle: all instances of Window
        # (i.e. toplevel XDG windows and regular X11 windows) have one. If a user uses
        # the static() command to convert one of these into a Static, that Static will
        # keep the same handle. However, Static windows can also be layer shell windows
        # or non-regular X11 clients (e.g. X11 bars or popups), and so might not have a
        # handle. Because we pass ownership of the handle to a Static during static(),
        # and the old Window would destroy the handle during finalize(), we make this
        # attribute optional to avoid the destroy().
        self.ftm_handle: ftm.ForeignToplevelHandleV1 | None = None

    def finalize(self) -> None:
        self.finalize_listeners()
        self.surface.data = None

        # Remove the scene graph container. Any borders will die with it.
        self.container.node.data = None
        self.container.node.destroy()
        del self.data_handle

        if self.ftm_handle:
            self.ftm_handle.destroy()
            self.ftm_handle = None

        self.core.remove_pointer_constraints(self)

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: window map")
        self.unhide()

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: window unmap")
        self.hide()

    @property
    def wid(self) -> int:
        return self._wid

    @property
    def group(self) -> _Group | None:
        return self._group

    @group.setter
    def group(self, group: _Group | None) -> None:
        self._group = group

    @property
    def urgent(self) -> bool:
        return self._urgent

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: window destroy")
        self.hide()

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
        else:
            self.qtile.unmanage(self.wid)

        self.finalize()

    def _on_foreign_request_maximize(
        self, _listener: Listener, event: ftm.ForeignToplevelHandleV1MaximizedEvent
    ) -> None:
        logger.debug("Signal: foreign_toplevel_management request_maximize")
        self.maximized = event.maximized

    def _on_foreign_request_minimize(
        self, _listener: Listener, event: ftm.ForeignToplevelHandleV1MinimizedEvent
    ) -> None:
        logger.debug("Signal: foreign_toplevel_management request_minimize")
        self.minimized = event.minimized

    def _on_foreign_request_fullscreen(
        self, _listener: Listener, event: ftm.ForeignToplevelHandleV1FullscreenEvent
    ) -> None:
        logger.debug("Signal: foreign_toplevel_management request_fullscreen")
        self.fullscreen = event.fullscreen

    def _on_foreign_request_activate(
        self, _listener: Listener, event: ftm.ForeignToplevelHandleV1ActivatedEvent
    ) -> None:
        logger.debug("Signal: foreign_toplevel_management request_activate")
        if self.group:
            self.qtile.current_screen.set_group(self.group)
            self.group.focus(self)

    def _on_foreign_request_close(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: foreign_toplevel_management request_close")
        self.kill()

    def _on_inhibitor_destroy(self, listener: Listener, surface: Surface) -> None:
        # We don't have reference to the inhibitor, but it doesn't really
        # matter we only need to keep count of how many inhibitors there are
        self._idle_inhibitors_count -= 1
        listener.remove()
        if self._idle_inhibitors_count == 0:
            self.core.check_idle_inhibitor()
            # TODO: do we also need to check idle inhibitors when unmapping?

    def hide(self) -> None:
        self.container.node.set_enabled(enabled=False)
        seat = self.core.seat
        if not seat.destroyed:
            if self.surface.surface == seat.keyboard_state.focused_surface:
                seat.keyboard_clear_focus()

    def get_wm_class(self) -> list | None:
        if self._wm_class:
            return [self._wm_class]
        return None

    def belongs_to_client(self, other: Client) -> bool:
        return other == Client.from_resource(self.surface.surface._ptr.resource)

    def focus(self, warp: bool = True) -> None:
        self._urgent = False
        self.core.focus_window(self)

        if warp and self.qtile.config.cursor_warp:
            self.core.warp_pointer(
                self.x + self._width / 2,
                self.y + self._height / 2,
            )

        if self.group and self.group.current_window is not self:
            self.group.focus(self)

        hook.fire("client_focus", self)

    def togroup(
        self, group_name: str | None = None, *, switch_group: bool = False, toggle: bool = False
    ) -> None:
        """
        Move window to a specified group

        Also switch to that group if switch_group is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.
        """
        if group_name is None:
            group = self.qtile.current_group
        else:
            if group_name not in self.qtile.groups_map:
                raise CommandError(f"No such group: {group_name}")
            group = self.qtile.groups_map[group_name]

        if self.group is group:
            if toggle and self.group.screen.previous_group:
                group = self.group.screen.previous_group
            else:
                return

        self.hide()
        if self.group:
            if self.group.screen:
                # for floats remove window offset
                self.x -= self.group.screen.x
            group_ref = self.group
            self.group.remove(self)
            # delete groups with `persist=False`
            if (
                not self.qtile.dgroups.groups_map[group_ref.name].persist
                and len(group_ref.windows) <= 1
            ):
                # set back original group so _del() can grab it
                self.group = group_ref
                self.qtile.dgroups._del(self)
                self.group = None

        if group.screen and self.x < group.screen.x:
            self.x += group.screen.x
        group.add(self)
        if switch_group:
            group.toscreen(toggle=toggle)

    def paint_borders(self, colors: ColorsType | None, width: int) -> None:
        if not colors:
            colors = []
            width = 0

        if not isinstance(colors, list):
            colors = [colors]

        if self.tree:
            self.tree.node.set_position(width, width)
        self.bordercolor = colors
        self.borderwidth = width

        if width == 0:
            for rects in self._borders:
                for rect in rects:
                    rect.node.destroy()
            self._borders.clear()
            return

        if len(colors) > width:
            colors = colors[:width]

        num = len(colors)
        old_borders = self._borders
        new_borders = []
        widths = [width // num] * num
        for i in range(width % num):
            widths[i] += 1

        outer_w = self.width + width * 2
        outer_h = self.height + width * 2
        coord = 0

        for i, color in enumerate(colors):
            color_ = _rgb(color)
            bw = widths[i]

            # [x, y, width, height] for N, E, S, W
            geometries = (
                (coord, coord, outer_w - coord * 2, bw),
                (outer_w - bw - coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
                (coord, outer_h - bw - coord, outer_w - coord * 2, bw),
                (coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
            )

            if old_borders:
                rects = old_borders.pop(0)
                for (x, y, w, h), rect in zip(geometries, rects):
                    rect.set_color(color_)
                    rect.set_size(w, h)
                    rect.node.set_position(x, y)

            else:
                rects = []
                for x, y, w, h in geometries:
                    rect = SceneRect(self.container, w, h, color_)
                    rect.node.set_position(x, y)
                    rects.append(rect)

            new_borders.append(rects)
            coord += bw

        for rects in old_borders:
            for rect in rects:
                rect.node.destroy()

        # Ensure the window contents and any nested surfaces are drawn above the
        # borders.
        if self.tree:
            self.tree.node.raise_to_top()

        self._borders = new_borders

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, opacity: float) -> None:
        self._opacity = opacity
        self.core.configure_node_opacity(self.container.node)

    @property
    def floating(self) -> bool:
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float: bool) -> None:
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                if not self._float_width:  # These might start as 0
                    self._float_width = self._width
                    self._float_height = self._height
                self._reconfigure_floating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self._float_width,
                    self._float_height,
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            self._update_fullscreen(False)
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self._float_width = self._width
                self._float_height = self._height
            self._float_state = FloatStates.NOT_FLOATING
            if self.group:
                self.group.mark_floating(self, False)
            hook.fire("float_change")

    @property
    def fullscreen(self) -> bool:
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        if do_full and self._float_state != FloatStates.FULLSCREEN:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.fullscreen_border_width if self.group else 0
            self._reconfigure_floating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
        elif self._float_state == FloatStates.FULLSCREEN:
            self._restore_geometry()
            self.floating = False

    @abc.abstractmethod
    def _update_fullscreen(self, do_full: bool) -> None:
        pass

    @property
    def maximized(self) -> bool:
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize: bool) -> None:
        if do_maximize:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.max_border_width if self.group else 0
            self._reconfigure_floating(
                screen.dx,
                screen.dy,
                screen.dwidth - 2 * bw,
                screen.dheight - 2 * bw,
                new_float_state=FloatStates.MAXIMIZED,
            )
        else:
            if self._float_state == FloatStates.MAXIMIZED:
                self._restore_geometry()
                self.floating = False

        if self.ftm_handle:
            self.ftm_handle.set_maximized(do_maximize)

    @property
    def minimized(self) -> bool:
        return self._float_state == FloatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize: bool) -> None:
        if do_minimize:
            if self._float_state != FloatStates.MINIMIZED:
                self._reconfigure_floating(new_float_state=FloatStates.MINIMIZED)
        else:
            if self._float_state == FloatStates.MINIMIZED:
                self.floating = False

        if self.ftm_handle:
            self.ftm_handle.set_minimized(do_minimize)

    def _tweak_float(
        self,
        x: int | None = None,
        y: int | None = None,
        dx: int = 0,
        dy: int = 0,
        w: int | None = None,
        h: int | None = None,
        dw: int = 0,
        dh: int = 0,
    ) -> None:
        if x is None:
            x = self.x
        x += dx

        if y is None:
            y = self.y
        y += dy

        if w is None:
            w = self._width
        w += dw

        if h is None:
            h = self._height
        h += dh

        if h < 0:
            h = 0
        if w < 0:
            w = 0

        screen = self.qtile.find_closest_screen(x + w // 2, y + h // 2)
        if self.group and screen is not None and screen != self.group.screen:
            self.group.remove(self, force=True)
            screen.group.add(self, force=True)
            self.qtile.focus_screen(screen.index)

        self._reconfigure_floating(x, y, w, h)

    def _reconfigure_floating(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
        new_float_state: FloatStates = FloatStates.FLOATING,
    ) -> None:
        self._update_fullscreen(new_float_state == FloatStates.FULLSCREEN)
        if new_float_state == FloatStates.MINIMIZED:
            self.hide()
        else:
            self.place(
                x, y, w, h, self.borderwidth, self.bordercolor, above=True, respect_hints=True
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire("float_change")

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        float_info = {
            "x": self.float_x,
            "y": self.float_y,
            "width": self._float_width,
            "height": self._float_height,
        }
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self._width,
            height=self._height,
            group=self.group.name if self.group else None,
            id=self.wid,
            wm_class=self.get_wm_class(),
            shell="XDG" if self.__class__.__name__ == "XdgWindow" else "XWayland",
            float_info=float_info,
            floating=self._float_state != FloatStates.NOT_FLOATING,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN,
        )

    def match(self, match: config._Match) -> bool:
        return match.compare(self)

    def add_idle_inhibitor(
        self,
        surface: Surface,
        _x: int,
        _y: int,
        inhibitor: IdleInhibitorV1,
    ) -> None:
        if surface == inhibitor.surface:
            self._idle_inhibitors_count += 1
            inhibitor.data = self
            self.add_listener(inhibitor.destroy_event, self._on_inhibitor_destroy)
            if self._idle_inhibitors_count == 1:
                self.core.check_idle_inhibitor()

    @property
    def is_idle_inhibited(self) -> bool:
        return self._idle_inhibitors_count > 0

    def _items(self, name: str) -> ItemT:
        if name == "group":
            return True, []
        if name == "layout":
            if self.group:
                return True, list(range(len(self.group.layouts)))
            return None
        if name == "screen":
            if self.group and self.group.screen:
                return True, []
        return None

    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout if self.group else None
            else:
                return utils.lget(self.group.layouts, int(sel)) if self.group else None
        elif name == "screen":
            return self.group.screen if self.group else None
        return None

    @expose_command()
    def move_floating(self, dx: int, dy: int) -> None:
        self._tweak_float(dx=dx, dy=dy)

    @expose_command()
    def resize_floating(self, dw: int, dh: int) -> None:
        self._tweak_float(dw=dw, dh=dh)

    @expose_command()
    def set_position_floating(self, x: int, y: int) -> None:
        self._tweak_float(x=x, y=y)

    @expose_command()
    def set_position(self, x: int, y: int) -> None:
        if self.floating:
            self._tweak_float(x=x, y=y)
            return

        if self.group:
            cx = self.core.cursor.x
            cy = self.core.cursor.y
            for window in self.group.windows:
                if (
                    window is not self
                    and not window.floating
                    and window.x <= cx <= (window.x + window.width)
                    and window.y <= cy <= (window.y + window.height)
                ):
                    self.group.layout.swap(self, window)
                    return

    @expose_command()
    def set_size_floating(self, w: int, h: int) -> None:
        self._tweak_float(w=w, h=h)

    @expose_command()
    def get_position(self) -> tuple[int, int]:
        return self.x, self.y

    @expose_command()
    def get_size(self) -> tuple[int, int]:
        return self._width, self._height

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
    def bring_to_front(self) -> None:
        self.container.node.raise_to_top()

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        # The concrete Window class must fire the client_managed hook after it's
        # completed any custom logic.
        self.defunct = True
        if self.group:
            self.group.remove(self)

        # Keep track of user-specified geometry to support X11.
        # Respect configure requests only if these are `None` here.
        conf_x = x
        conf_y = y
        conf_width = width
        conf_height = height

        if x is None:
            x = self.x + self.borderwidth
        if y is None:
            y = self.y + self.borderwidth
        if width is None:
            width = self._width
        if height is None:
            height = self._height

        self.finalize_listeners()

        # Destroy the borders. Currently static windows are always borderless.
        while self._borders:
            for rect in self._borders.pop():
                rect.node.destroy()
        if self.tree:
            self.tree.node.set_position(0, 0)

        win = self._to_static(conf_x, conf_y, conf_width, conf_height)

        # Pass ownership of the foreign toplevel handle to the static window.
        if self.ftm_handle:
            win.ftm_handle = self.ftm_handle
            self.ftm_handle = None
            win.add_listener(win.ftm_handle.request_close_event, win._on_foreign_request_close)

        if screen is not None:
            win.screen = self.qtile.screens[screen]
        win.unhide()
        win.place(x, y, width, height, 0, None)
        self.qtile.windows_map[self.wid] = win

    @expose_command()
    def is_visible(self) -> bool:
        return self.container.node.enabled

    @abc.abstractmethod
    def _to_static(
        self, x: int | None, y: int | None, width: int | None, height: int | None
    ) -> Static:
        # This must return a new `Static` subclass instance
        pass


class Static(typing.Generic[S], _Base, base.Static, HasListeners):
    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: S,
        wid: int,
        idle_inhibitor_count: int = 0,
    ):
        base.Static.__init__(self)
        self.core = core
        self.qtile = qtile
        self.surface = surface
        self.screen = qtile.current_screen
        self._wid = wid
        self.x = 0
        self.y = 0
        self._width = 0
        self._height = 0
        self.borderwidth: int = 0
        self.bordercolor: list[ffi.CData] = [_rgb((0, 0, 0, 1))]
        self.opacity: float = 1.0
        self._wm_class: str | None = None
        self._idle_inhibitors_count = idle_inhibitor_count
        self.ftm_handle: ftm.ForeignToplevelHandleV1 | None = None
        self.data_handle = ffi.new_handle(self)
        surface.data = self.data_handle
        self._urgent = False

    def finalize(self) -> None:
        self.finalize_listeners()
        self.surface.data = None
        self.core.remove_pointer_constraints(self)
        del self.data_handle

    @property
    def wid(self) -> int:
        return self._wid

    @property
    def urgent(self) -> bool:
        return self._urgent

    def focus(self, warp: bool = True) -> None:
        self._urgent = False
        self.core.focus_window(self)

        if warp and self.qtile.config.cursor_warp:
            self.core.warp_pointer(
                self.x + self._width / 2,
                self.y + self._height / 2,
            )

        hook.fire("client_focus", self)

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static map")
        self.unhide()
        self.focus(True)
        self.bring_to_front()

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static unmap")
        self.hide()

    def hide(self) -> None:
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static destroy")
        self.hide()

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
        else:
            self.qtile.unmanage(self.wid)

        self.finalize()

    def _on_foreign_request_close(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: foreign_toplevel_management static request_close")
        self.kill()

    def _on_inhibitor_destroy(self, listener: Listener, surface: Surface) -> None:
        # We don't have reference to the inhibitor, but it doesn't really
        # matter we only need to keep count of how many inhibitors there are
        self._idle_inhibitors_count -= 1
        listener.remove()
        if self._idle_inhibitors_count == 0:
            self.core.check_idle_inhibitor()

    def add_idle_inhibitor(
        self,
        surface: Surface,
        _x: int,
        _y: int,
        inhibitor: IdleInhibitorV1,
    ) -> None:
        if surface == inhibitor.surface:
            self._idle_inhibitors_count += 1
            inhibitor.data = self
            self.add_listener(inhibitor.destroy_event, self._on_inhibitor_destroy)
            if self._idle_inhibitors_count == 1:
                self.core.check_idle_inhibitor()

    @property
    def is_idle_inhibited(self) -> bool:
        return self._idle_inhibitors_count > 0

    def belongs_to_client(self, other: Client) -> bool:
        return other == Client.from_resource(self.surface.surface._ptr.resource)

    @expose_command()
    def bring_to_front(self) -> None:
        self.container.node.raise_to_top()

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        info = base.Static.info(self)
        cls_name = self.__class__.__name__
        if cls_name == "XdgStatic":
            info["shell"] = "XDG"
        elif cls_name == "XStatic":
            info["shell"] = "XWayland"
        else:
            info["shell"] = "layer"
        return info


class Internal(_Base, base.Internal):
    """
    Internal windows are simply textures controlled by the compositor.
    """

    def __init__(self, core: Core, qtile: Qtile, x: int, y: int, width: int, height: int):
        self.core = core
        self.qtile = qtile
        self._wid: int = self.core.new_wid()
        self.x: int = x
        self.y: int = y
        self._width: int = width
        self._height: int = height
        self._opacity: float = 1.0

        # Store this object on the scene node for finding the window under the pointer.
        self.wlr_buffer, self.surface = self._new_buffer(init=True)
        self.tree = SceneTree.create(core.mid_window_tree)
        self.data_handle = ffi.new_handle(self)
        self.tree.node.set_enabled(enabled=False)
        self.tree.node.data = self.data_handle
        self.tree.node.set_position(x, y)
        scene_buffer = SceneBuffer.create(self.tree, self.wlr_buffer)
        if scene_buffer is None:
            raise RuntimeError("Couldn't create scene buffer")
        self._scene_buffer = scene_buffer
        wlr_lib.wlr_scene_buffer_set_dest_size(scene_buffer._ptr, width, height)
        # The borders are wlr_scene_rects.
        # Inner list: N, E, S, W edges
        # Outer list: outside-in borders i.e. multiple for multiple borders
        self._borders: list[list[SceneRect]] = []
        self.bordercolor: ColorsType = "000000"

    def finalize(self) -> None:
        self.hide()

    def _new_buffer(self, init: bool = False) -> tuple[Buffer, cairocffi.ImageSurface]:
        if not init:
            self.wlr_buffer.drop()

        scale = self.qtile.config.wl_scale_factor
        width = int(self._width * scale)
        height = int(self._height * scale)
        surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
        stride = surface.get_stride()
        data = cairocffi.cairo.cairo_image_surface_get_data(surface._pointer)
        wlr_buffer = lib.cairo_buffer_create(width, height, stride, data)
        if wlr_buffer == ffi.NULL:
            raise RuntimeError("Couldn't allocate cairo buffer.")

        buffer = Buffer(wlr_buffer)

        if not init:
            self._scene_buffer.set_buffer_with_damage(buffer)
            wlr_lib.wlr_scene_buffer_set_dest_size(
                self._scene_buffer._ptr, self._width, self._height
            )

        return buffer, surface

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    def hide(self) -> None:
        self.tree.node.set_enabled(enabled=False)

    def unhide(self) -> None:
        self.tree.node.set_enabled(enabled=True)

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        self.core.focus_window(self)

    @expose_command()
    def kill(self) -> None:
        self.hide()
        if self.wid in self.qtile.windows_map:
            # It will be present during config reloads; absent during shutdown as this
            # will follow graceful_shutdown
            del self.qtile.windows_map[self.wid]

    @expose_command()
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
        if above:
            self.bring_to_front()

        self.x = x
        self.y = y
        self.tree.node.set_position(x, y)

        if width != self._width or height != self._height:
            # Changed size, we need to regenerate the buffer
            self._width = width
            self._height = height
            self.wlr_buffer, self.surface = self._new_buffer()

    def paint_borders(self, colors: ColorsType | None, width: int) -> None:
        if not colors:
            colors = []
            width = 0

        if not isinstance(colors, list):
            colors = [colors]

        if self._scene_buffer:
            self._scene_buffer.node.set_position(width, width)
        self.bordercolor = colors
        self.borderwidth = width

        if width == 0:
            for rects in self._borders:
                for rect in rects:
                    rect.node.destroy()
            self._borders.clear()
            return

        if len(colors) > width:
            colors = colors[:width]

        num = len(colors)
        old_borders = self._borders
        new_borders = []
        widths = [width // num] * num
        for i in range(width % num):
            widths[i] += 1

        outer_w = self.width + width * 2
        outer_h = self.height + width * 2
        coord = 0

        for i, color in enumerate(colors):
            color_ = _rgb(color)
            bw = widths[i]

            # [x, y, width, height] for N, E, S, W
            geometries = (
                (coord, coord, outer_w - coord * 2, bw),
                (outer_w - bw - coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
                (coord, outer_h - bw - coord, outer_w - coord * 2, bw),
                (coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
            )

            if old_borders:
                rects = old_borders.pop(0)
                for (x, y, w, h), rect in zip(geometries, rects):
                    rect.set_color(color_)
                    rect.set_size(w, h)
                    rect.node.set_position(x, y)

            else:
                rects = []
                for x, y, w, h in geometries:
                    rect = SceneRect(self.tree, w, h, color_)
                    rect.node.set_position(x, y)
                    rects.append(rect)

            new_borders.append(rects)
            coord += bw

        for rects in old_borders:
            for rect in rects:
                rect.node.destroy()

        # Ensure the window contents and any nested surfaces are drawn above the
        # borders.
        if self._scene_buffer:
            self._scene_buffer.node.raise_to_top()

        self._borders = new_borders

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        return dict(
            x=self.x,
            y=self.y,
            width=self._width,
            height=self._height,
            id=self.wid,
        )

    @expose_command()
    def bring_to_front(self) -> None:
        self.tree.node.raise_to_top()


WindowType = Window | Static | Internal


class PointerConstraint(HasListeners):
    """
    A small object to listen to signals on `struct wlr_pointer_constraint_v1` instances.
    """

    rect: Box

    def __init__(self, core: Core, wlr_constraint: PointerConstraintV1):
        self.core = core
        self.wlr_constraint = wlr_constraint
        self._warp_target: tuple[float, float] = (0, 0)
        self._needs_warp: bool = False

        assert core.qtile is not None
        owner = None

        for win in core.qtile.windows_map.values():
            if isinstance(win, (Window | Static)):
                if win.surface.surface == self.wlr_constraint.surface:
                    owner = win
                    break

        if owner is None:
            logger.error("No window found for pointer constraints. Please report.")
            raise RuntimeError

        self.window: Window | Static = owner

        self.add_listener(wlr_constraint.set_region_event, self._on_set_region)
        self.add_listener(wlr_constraint.destroy_event, self._on_destroy)

    def finalize(self) -> None:
        if self.core.active_pointer_constraint is self:
            self.disable()
        self.finalize_listeners()
        self.core.pointer_constraints.remove(self)

    def _on_set_region(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: wlr_pointer_constraint_v1 set_region")
        self._get_region()

    def _on_destroy(self, _listener: Listener, wlr_constraint: PointerConstraintV1) -> None:
        logger.debug("Signal: wlr_pointer_constraint_v1 destroy")
        self.finalize()

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        if self._needs_warp:
            # Warp in case the pointer is not inside the rect
            if not self.rect.contains_point(self.core.cursor.x, self.core.cursor.y):
                self.core.warp_pointer(*self._warp_target)
            self._needs_warp = False

    def _get_region(self) -> None:
        rect = self.wlr_constraint.region.rectangles_as_boxes()[0]
        rect.x += self.window.x + self.window.borderwidth
        rect.y += self.window.y + self.window.borderwidth
        self._warp_target = (rect.x + rect.width / 2, rect.y + rect.height / 2)
        self.rect = rect
        self._needs_warp = True

    def enable(self) -> None:
        logger.debug("Enabling pointer constraints.")
        self.core.active_pointer_constraint = self
        self._get_region()
        self.add_listener(self.wlr_constraint.surface.commit_event, self._on_commit)
        self.wlr_constraint.send_activated()

    def disable(self) -> None:
        logger.debug("Disabling pointer constraints.")

        if self.wlr_constraint.current.committed & PointerConstraintV1StateField.CURSOR_HINT:
            x, y = self.wlr_constraint.current.cursor_hint
            self.core.warp_pointer(x + self.window.x, y + self.window.y)

        self.core.active_pointer_constraint = None
        self.wlr_constraint.send_deactivated()
