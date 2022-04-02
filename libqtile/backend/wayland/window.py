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
import pywayland
import wlroots.wlr_types.foreign_toplevel_management_v1 as ftm
from pywayland.server import Listener
from wlroots import PtrHasData, ffi, xwayland
from wlroots.util.box import Box
from wlroots.util.edges import Edges
from wlroots.wlr_types import Texture
from wlroots.wlr_types.idle_inhibit_v1 import IdleInhibitorV1
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1Layer, LayerSurfaceV1
from wlroots.wlr_types.pointer_constraints_v1 import (
    PointerConstraintV1,
    PointerConstraintV1StateField,
)
from wlroots.wlr_types.xdg_shell import XdgPopup, XdgSurface, XdgTopLevelSetFullscreenEvent

from libqtile import config, hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.drawer import Drawer
from libqtile.backend.wayland.wlrq import DRM_FORMAT_ARGB8888, HasListeners
from libqtile.command.base import CommandError
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

    from wlroots.wlr_types.surface import SubSurface as WlrSubSurface
    from wlroots.wlr_types.surface import Surface

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.output import Output
    from libqtile.command.base import CommandObject, ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorsType, ColorType

EDGES_TILED = Edges.TOP | Edges.BOTTOM | Edges.LEFT | Edges.RIGHT
EDGES_FLOAT = Edges.NONE

S = typing.TypeVar("S", bound=PtrHasData)


@functools.lru_cache()
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
        self._mapped: bool = False
        self.x = 0
        self.y = 0
        self.bordercolor: list[ffi.CData] = [_rgb((0, 0, 0, 1))]
        self._opacity: float = 1.0
        self._outputs: set[Output] = set()
        self._wm_class: str | None = None
        self._idle_inhibitors_count: int = 0

        self._width: int = 0
        self._height: int = 0
        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int = 0
        self._float_height: int = 0
        self._float_state = FloatStates.NOT_FLOATING

        surface.data = self.ftm_handle = core.foreign_toplevel_manager_v1.create_handle()

    def finalize(self) -> None:
        self.finalize_listeners()
        self.ftm_handle.destroy()

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
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        """We keep track of which windows are mapped so we know which to render"""
        if mapped == self._mapped:
            return
        self._mapped = mapped
        if mapped:
            self.core.mapped_windows.append(self)
        else:
            self.core.mapped_windows.remove(self)
        self.core.stack_windows()
        if self._idle_inhibitors_count > 0:
            self.core.check_idle_inhibitor()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: window destroy")
        if self.mapped:
            logger.warning("Window destroyed before unmap event.")
            self.mapped = False

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
        else:
            self.qtile.unmanage(self.wid)

        self.finalize()

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        self.damage()

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

    def _find_outputs(self) -> None:
        """Find the outputs on which this window can be seen."""
        self._outputs = set(o for o in self.core.outputs if o.contains(self))

    def damage(self) -> None:
        for output in self._outputs:
            output.damage()

    def get_wm_class(self) -> list | None:
        if self._wm_class:
            return [self._wm_class]
        return None

    def focus(self, warp: bool) -> None:
        self.core.focus_window(self)

        if warp and self.qtile.config.cursor_warp:
            self.core.warp_pointer(
                self.x + self.width / 2,
                self.y + self.height / 2,
            )

        if self.group:
            self.group.current_window = self

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
                raise CommandError("No such group: %s" % group_name)
            group = self.qtile.groups_map[group_name]

        if self.group is group:
            if toggle and hasattr(self.group.screen, "previous_group"):
                group = self.group.screen.previous_group
            else:
                return

        self.hide()
        if self.group:
            if self.group.screen:
                # for floats remove window offset
                self.x -= self.group.screen.x
            self.group.remove(self)

        if group.screen and self.x < group.screen.x:
            self.x += group.screen.x
        group.add(self)
        if switch_group:
            group.cmd_toscreen(toggle=toggle)

    def paint_borders(self, color: ColorsType | None, width: int) -> None:
        if color:
            if isinstance(color, list):
                if len(color) > width:
                    color = color[:width]
                self.bordercolor = [_rgb(c) for c in color]
            else:
                self.bordercolor = [_rgb(color)]
        self.borderwidth = width

    @property
    def floating(self) -> bool:
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float: bool) -> None:
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                if not self._float_width:  # These might start as 0
                    self._float_width = self.width
                    self._float_height = self.height
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
                self._float_width = self.width
                self._float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            if self.group:
                self.group.mark_floating(self, False)
            hook.fire("float_change")

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
                self.floating = False

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
            w = self.width
        w += dw

        if h is None:
            h = self.height
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
            width=self.width,
            height=self.height,
            group=self.group.name if self.group else None,
            id=self.wid,
            wm_class=self.get_wm_class(),
            float_info=float_info,
            floating=self._float_state != FloatStates.NOT_FLOATING,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN,
        )

    def match(self, match: config.Match) -> bool:
        return match.compare(self)

    def add_idle_inhibitor(
        self, surface: Surface, _x: int, _y: int, inhibitor: IdleInhibitorV1 | None
    ) -> None:
        if inhibitor and surface == inhibitor.surface:
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
                return utils.lget(self.group.layouts, sel) if self.group else None
        elif name == "screen":
            return self.group.screen if self.group else None
        return None

    def cmd_focus(self, warp: bool = True) -> None:
        """Focuses the window."""
        self.focus(warp)

    def cmd_move_floating(self, dx: int, dy: int) -> None:
        self._tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw: int, dh: int) -> None:
        self._tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x: int, y: int) -> None:
        self._tweak_float(x=x, y=y)

    def cmd_set_position(self, x: int, y: int) -> None:
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
                    clients = self.group.layout.clients
                    index1 = clients.index(self)
                    index2 = clients.index(window)
                    clients[index1], clients[index2] = clients[index2], clients[index1]
                    self.group.layout.focused = index2
                    self.group.layout_all()
                    return

    def cmd_set_size_floating(self, w: int, h: int) -> None:
        self._tweak_float(w=w, h=h)

    def cmd_place(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        borderwidth: int,
        bordercolor: ColorsType | None,
        above: bool = False,
        margin: int | None = None,
    ) -> None:
        self.place(x, y, width, height, borderwidth, bordercolor, above, margin)

    def cmd_get_position(self) -> tuple[int, int]:
        return self.x, self.y

    def cmd_get_size(self) -> tuple[int, int]:
        return self.width, self.height

    def cmd_toggle_floating(self) -> None:
        self.floating = not self.floating

    def cmd_enable_floating(self) -> None:
        self.floating = True

    def cmd_disable_floating(self) -> None:
        self.floating = False

    def cmd_toggle_maximize(self) -> None:
        self.maximized = not self.maximized

    def cmd_toggle_minimize(self) -> None:
        self.minimized = not self.minimized

    def cmd_toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    def cmd_enable_fullscreen(self) -> None:
        self.fullscreen = True

    def cmd_disable_fullscreen(self) -> None:
        self.fullscreen = False

    def cmd_bring_to_front(self) -> None:
        if self.mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()

    def cmd_kill(self) -> None:
        self.kill()

    def cmd_static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        # The concrete Window type must fire the client_managed hook after it's
        # completed any custom logic.
        self.defunct = True
        if self.group:
            self.group.remove(self)
        if x is None:
            x = self.x + self.borderwidth
        if y is None:
            y = self.y + self.borderwidth
        if width is None:
            width = self.width
        if height is None:
            height = self.height

        self.finalize_listeners()
        win = self._to_static()
        if screen is not None:
            win.screen = self.qtile.screens[screen]
        win.mapped = True
        win.place(x, y, width, height, 0, None)
        self.qtile.windows_map[self.wid] = win
        if self in self.core.mapped_windows:
            self.core.mapped_windows.remove(self)
        self.core.stack_windows()

    @abc.abstractmethod
    def _to_static(self) -> Static:
        # This must return a new `base.Static` subclass instance
        pass


class XdgWindow(Window[XdgSurface]):
    """An Wayland client connecting via the xdg shell."""

    def __init__(self, core: Core, qtile: Qtile, surface: XdgSurface):
        Window.__init__(self, core, qtile, surface)

        self._wm_class = surface.toplevel.app_id
        self.popups: list[XdgPopupWindow] = []
        self.subsurfaces: list[SubSurface] = []

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.new_popup_event, self._on_new_popup)
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.surface.new_subsurface_event, self._on_new_subsurface)

    def finalize(self) -> None:
        Window.finalize(self)
        for subsurface in self.subsurfaces:
            subsurface.finalize()

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.finalize()

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow map")

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
            self._wid = self.core.new_wid()
            logger.debug(f"Managing new top-level window with window ID: {self.wid}")

            # Save the client's desired geometry
            surface = self.surface
            geometry = surface.get_geometry()
            self._width = self._float_width = geometry.width
            self._height = self._float_height = geometry.height

            # Tell the client to render tiled edges
            surface.set_tiled(EDGES_TILED)

            # Get the client's name
            if surface.toplevel.title:
                self.name = surface.toplevel.title
                self.ftm_handle.set_title(self.name)
            if self._wm_class:
                self.ftm_handle.set_app_id(self._wm_class or "")

            # Add the toplevel's listeners
            self.add_listener(
                surface.toplevel.request_fullscreen_event, self._on_request_fullscreen
            )
            self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
            self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)
            self.add_listener(
                self.ftm_handle.request_maximize_event, self._on_foreign_request_maximize
            )
            self.add_listener(
                self.ftm_handle.request_minimize_event, self._on_foreign_request_minimize
            )
            self.add_listener(
                self.ftm_handle.request_activate_event, self._on_foreign_request_activate
            )
            self.add_listener(
                self.ftm_handle.request_fullscreen_event, self._on_foreign_request_fullscreen
            )
            self.add_listener(self.ftm_handle.request_close_event, self._on_foreign_request_close)

            self.qtile.manage(self)

        if self.group and self.group.screen:
            self.mapped = True
            self.core.focus_window(self)

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow unmap")
        self.mapped = False
        self.damage()
        seat = self.core.seat
        if not seat.destroyed:
            if self.surface.surface == seat.keyboard_state.focused_surface:
                seat.keyboard_clear_focus()

    def _on_new_popup(self, _listener: Listener, xdg_popup: XdgPopup) -> None:
        logger.debug("Signal: xdgwindow new_popup")
        self.popups.append(XdgPopupWindow(self, xdg_popup))

    def _on_new_subsurface(self, _listener: Listener, subsurface: WlrSubSurface) -> None:
        self.subsurfaces.append(SubSurface(self, subsurface))

    def _on_request_fullscreen(
        self, _listener: Listener, event: XdgTopLevelSetFullscreenEvent
    ) -> None:
        logger.debug("Signal: xdgwindow request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            self.fullscreen = event.fullscreen

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow set_title")
        title = self.surface.toplevel.title
        if title and title != self.name:
            self.name = title
            self.ftm_handle.set_title(self.name)
            hook.fire("client_name_updated", self)

    def _on_set_app_id(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow set_app_id")
        self._wm_class = self.surface.toplevel.app_id
        self.ftm_handle.set_app_id(self._wm_class or "")

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

    def kill(self) -> None:
        self.surface.send_close()

    def has_fixed_size(self) -> bool:
        state = self.surface.toplevel._ptr.current
        return 0 < state.min_width == state.max_width and 0 < state.min_height == state.max_height

    def is_transient_for(self) -> base.WindowType | None:
        """What window is this window a transient window for?"""
        parent = self.surface.toplevel.parent
        if parent:
            for win in self.qtile.windows_map.values():
                if isinstance(win, XdgWindow) and win.surface == parent:
                    return win
        return None

    def get_pid(self) -> int:
        pid = pywayland.ffi.new("pid_t *")
        pywayland.lib.wl_client_get_credentials(
            self.surface._ptr.client.client, pid, ffi.NULL, ffi.NULL
        )
        return pid[0]

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self.surface.set_fullscreen(do_full)
            self.ftm_handle.set_fullscreen(do_full)

    @property
    def fullscreen(self) -> bool:
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        self.surface.set_fullscreen(do_full)
        if do_full:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )
            if self.group:
                bw = self.group.floating_layout.fullscreen_border_width
            else:
                bw = 0
            self._reconfigure_floating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
        elif self._float_state == FloatStates.FULLSCREEN:
            self.floating = False

        self.ftm_handle.set_fullscreen(do_full)

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
        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        if respect_hints:
            state = self.surface.toplevel._ptr.current
            width = max(width, state.min_width)
            height = max(height, state.min_height)
            if state.max_width:
                width = min(width, state.max_width)
            if state.max_height:
                height = min(height, state.max_height)

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self._width = int(width)
        self._height = int(height)
        self.surface.set_size(self._width, self._height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.cmd_bring_to_front()

        prev_outputs = self._outputs.copy()
        self._find_outputs()
        for output in self._outputs | prev_outputs:
            output.damage()

    def cmd_static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        Window.cmd_static(self, screen, x, y, width, height)
        win = self.qtile.windows_map[self._wid]
        assert isinstance(win, XdgStatic)
        win.subsurfaces = self.subsurfaces

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.window = win
                break

        hook.fire("client_managed", win)

    def _to_static(self) -> XdgStatic:
        return XdgStatic(
            self.core, self.qtile, self.surface, self.wid, self._idle_inhibitors_count
        )


class XWindow(Window[xwayland.Surface]):
    """An X11 client connecting via XWayland."""

    def __init__(self, core: Core, qtile: Qtile, surface: xwayland.Surface):
        Window.__init__(self, core, qtile, surface)

        self._wm_class = self.surface.wm_class
        self._unmapping: bool = False  # Whether the client or Qtile unmapped this

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow map")

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
            self._wid = self.core.new_wid()
            logger.debug(f"Managing new XWayland window with window ID: {self.wid}")

            # Make it static if it isn't a regular window
            if self.surface.override_redirect:
                self.cmd_static(
                    None, self.surface.x, self.surface.y, self.surface.width, self.surface.height
                )
                win = self.qtile.windows_map[self._wid]
                assert isinstance(win, XStatic)
                self.core.focus_window(win)
                return

            # Save the client's desired geometry. xterm seems to have these set to 1, so
            # let's ignore 1 or below. The float sizes will be fetched when it is floated.
            if self.surface.width > 1:
                self._width = self._float_width = self.surface.width
            if self.surface.height > 1:
                self._height = self._float_height = self.surface.height

            # Get the client's name and class
            title = self.surface.title
            if title:
                self.name = title
                self.ftm_handle.set_title(self.name)
            self._wm_class = self.surface.wm_class
            self.ftm_handle.set_app_id(self._wm_class or "")

            # Add event listeners
            self.add_listener(self.surface.surface.commit_event, self._on_commit)
            self.add_listener(self.surface.request_fullscreen_event, self._on_request_fullscreen)
            self.add_listener(self.surface.set_title_event, self._on_set_title)
            self.add_listener(self.surface.set_class_event, self._on_set_class)
            self.add_listener(
                self.ftm_handle.request_maximize_event, self._on_foreign_request_maximize
            )
            self.add_listener(
                self.ftm_handle.request_minimize_event, self._on_foreign_request_minimize
            )
            self.add_listener(
                self.ftm_handle.request_activate_event, self._on_foreign_request_activate
            )
            self.add_listener(
                self.ftm_handle.request_fullscreen_event, self._on_foreign_request_fullscreen
            )
            self.add_listener(self.ftm_handle.request_close_event, self._on_foreign_request_close)

            self.qtile.manage(self)

        if self.group and self.group.screen:
            self.mapped = True
            self.core.focus_window(self)

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow unmap")
        self.mapped = False
        self.damage()
        seat = self.core.seat
        if not seat.destroyed:
            if self.surface.surface == seat.keyboard_state.focused_surface:
                seat.keyboard_clear_focus()

        if not self._unmapping:
            self.qtile.unmanage(self.wid)
            self.finalize()

        self._unmapping = False

    def _on_request_fullscreen(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            self.fullscreen = not self.fullscreen

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow set_title")
        title = self.surface.title
        if title and title != self.name:
            self.name = title
            self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow set_class")
        self._wm_class = self.surface.wm_class
        self.ftm_handle.set_app_id(self._wm_class or "")

    def hide(self) -> None:
        if self.mapped:
            self._unmapping = True
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

    def kill(self) -> None:
        self.surface.close()

    def has_fixed_size(self) -> bool:
        hints = self.surface.size_hints
        # TODO: Maybe consider these flags too:
        # "PMinSize" in self.hints["flags"] and "PMaxSize" in self.hints["flags"]
        return bool(
            hints
            and 0 < hints.min_width == hints.max_width
            and 0 < hints.min_height == hints.max_height
        )

    def is_transient_for(self) -> base.WindowType | None:
        """What window is this window a transient window for?"""
        parent = self.surface.parent
        if parent:
            for win in self.qtile.windows_map.values():
                if isinstance(win, XWindow) and win.surface == parent:
                    return win
        return None

    def get_pid(self) -> int:
        return self.surface.pid

    def get_wm_type(self) -> str | None:
        wm_type = self.surface.window_type
        if wm_type:
            return self.core.xwayland_atoms[wm_type[0]]
        return None

    def get_wm_role(self) -> str | None:
        return self.surface.role

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self.surface.set_fullscreen(do_full)
            self.ftm_handle.set_fullscreen(do_full)

    @property
    def fullscreen(self) -> bool:
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        self.surface.set_fullscreen(do_full)
        if do_full:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )
            bw = self.group.floating_layout.fullscreen_border_width if self.group else 0
            self._reconfigure_floating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
        elif self._float_state == FloatStates.FULLSCREEN:
            self.floating = False

        self.ftm_handle.set_fullscreen(do_full)

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
        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        if respect_hints:
            hints = self.surface.size_hints
            if hints:
                width = max(width, hints.min_width)
                height = max(height, hints.min_height)
                if hints.max_width > 0:
                    width = min(width, hints.max_width)
                if hints.max_height > 0:
                    height = min(height, hints.max_height)

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self._width = int(width)
        self._height = int(height)
        self.surface.configure(x, y, self._width, self._height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.cmd_bring_to_front()

        prev_outputs = self._outputs.copy()
        self._find_outputs()
        for output in self._outputs | prev_outputs:
            output.damage()

    def cmd_static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        Window.cmd_static(self, screen, x, y, width, height)
        hook.fire("client_managed", self.qtile.windows_map[self._wid])

    def _to_static(self) -> XStatic:
        return XStatic(self.core, self.qtile, self.surface, self.wid, self._idle_inhibitors_count)


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
        self._mapped: bool = False
        self.x = 0
        self.y = 0
        self._width = 0
        self._height = 0
        self.borderwidth: int = 0
        self.bordercolor: list[ffi.CData] = [_rgb((0, 0, 0, 1))]
        self.opacity: float = 1.0
        self._outputs: set[Output] = set()
        self._wm_class: str | None = None
        self._idle_inhibitors_count = idle_inhibitor_count

        if surface.data:
            self.ftm_handle = surface.data
            self.add_listener(self.ftm_handle.request_close_event, self._on_foreign_request_close)

    def finalize(self) -> None:
        self.finalize_listeners()

    @property
    def wid(self) -> int:
        return self._wid

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        if mapped == self._mapped:
            return
        self._mapped = mapped

        if mapped:
            self.core.mapped_windows.append(self)
        else:
            self.core.mapped_windows.remove(self)

        self.core.stack_windows()

    def _find_outputs(self) -> None:
        self._outputs = set(o for o in self.core.outputs if o.contains(self))

    def damage(self) -> None:
        for output in self._outputs:
            output.damage()

    def focus(self, warp: bool) -> None:
        self.core.focus_window(self)

        if warp and self.qtile.config.cursor_warp:
            self.core.warp_pointer(
                self.x + self.width / 2,
                self.y + self.height / 2,
            )

        hook.fire("client_focus", self)

    def paint_borders(self, color: ColorsType | None, width: int) -> None:
        if color:
            if isinstance(color, list):
                if len(color) > width:
                    color = color[:width]
                self.bordercolor = [_rgb(c) for c in color]
            else:
                self.bordercolor = [_rgb(color)]
        self.borderwidth = width

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static map")
        self.mapped = True
        self.focus(True)

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static unmap")
        self.mapped = False
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:  # type: ignore
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()
        self.damage()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: static destroy")
        if self.mapped:
            logger.warning("Window destroyed before unmap event.")
            self.mapped = False

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
        else:
            self.qtile.unmanage(self.wid)

        self.finalize()

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        self.damage()

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
        self, surface: Surface, _x: int, _y: int, inhibitor: IdleInhibitorV1 | None
    ) -> None:
        if inhibitor and surface == inhibitor.surface:
            self._idle_inhibitors_count += 1
            inhibitor.data = self
            self.add_listener(inhibitor.destroy_event, self._on_inhibitor_destroy)
            if self._idle_inhibitors_count == 1:
                self.core.check_idle_inhibitor()

    @property
    def is_idle_inhibited(self) -> bool:
        return self._idle_inhibitors_count > 0

    def cmd_bring_to_front(self) -> None:
        if self.mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()
            self.damage()


class XdgStatic(Static[XdgSurface]):
    """A static window belonging to the XDG shell."""

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: XdgSurface,
        wid: int,
        idle_inhibitor_count: int,
    ):
        Static.__init__(
            self, core, qtile, surface, wid, idle_inhibitor_count=idle_inhibitor_count
        )
        self.subsurfaces: list[SubSurface] = []
        self._find_outputs()

        if surface.toplevel.title:
            self.name = surface.toplevel.title
        self._wm_class = surface.toplevel.app_id

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
        self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)

    def finalize(self) -> None:
        Static.finalize(self)
        for subsurface in self.subsurfaces:
            subsurface.finalize()

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.finalize()

    def kill(self) -> None:
        self.surface.send_close()

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

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
        self.x = x
        self.y = y
        self._width = width
        self._height = height
        self.surface.set_size(self._width, self._height)
        self.paint_borders(bordercolor, borderwidth)
        self._find_outputs()
        self.damage()

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgstatic set_title")
        title = self.surface.toplevel.title
        if title and title != self.name:
            self.name = title
            self.ftm_handle.set_title(self.name)
            hook.fire("client_name_updated", self)

    def _on_set_app_id(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgstatic set_app_id")
        self._wm_class = self.surface.toplevel.app_id
        self.ftm_handle.set_app_id(self._wm_class or "")


class XStatic(Static[xwayland.Surface]):
    """A static window belonging to the XWayland shell."""

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: xwayland.Surface,
        wid: int,
        idle_inhibitor_count: int,
    ):
        Static.__init__(
            self, core, qtile, surface, wid, idle_inhibitor_count=idle_inhibitor_count
        )
        self._wm_class = surface.wm_class
        self._find_outputs()

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.set_title_event, self._on_set_title)
        self.add_listener(surface.set_class_event, self._on_set_class)

    def kill(self) -> None:
        self.surface.close()

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

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
        self.x = x
        self.y = y
        self._width = width
        self._height = height
        self.surface.configure(x, y, self._width, self._height)
        self.paint_borders(bordercolor, borderwidth)
        self._find_outputs()
        self.damage()

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_title")
        title = self.surface.title
        if title and title != self.name:
            self.name = title
            self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_class")
        self._wm_class = self.surface.wm_class
        self.ftm_handle.set_app_id(self._wm_class or "")


class LayerStatic(Static[LayerSurfaceV1]):
    """A static window belonging to the layer shell."""

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: LayerSurfaceV1,
        wid: int,
    ):
        Static.__init__(self, core, qtile, surface, wid)
        self.subsurfaces: list[SubSurface] = []

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)

        self._layer = LayerShellV1Layer.BACKGROUND
        self.desired_width = 0
        self.desired_height = 0
        if surface.output is None:
            surface.output = core.output_layout.output_at(core.cursor.x, core.cursor.y)

        if surface.output:
            output = surface.output.data
            if output:
                self.output = output
                self.screen = self.output.screen

        self.mapped = True
        self._outputs.add(self.output)

    def finalize(self) -> None:
        Static.finalize(self)
        for subsurface in self.subsurfaces:
            subsurface.finalize()

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.finalize()

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        if mapped == self._mapped:
            return
        self._mapped = mapped

        self._layer = self.surface.pending.layer
        layer = self.output.layers[self._layer]
        if mapped:
            layer.append(self)
        else:
            layer.remove(self)

            if self.reserved_space:
                self.qtile.free_reserved_space(self.reserved_space, self.screen)
        self.output.organise_layers()

        self.core.stack_windows()

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: layerstatic map")
        self.mapped = True
        self.output.organise_layers()
        self.focus(True)

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: layerstatic unmap")
        self.mapped = False
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()
        self.output.organise_layers()
        self.damage()

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        current = self.surface.current
        if (
            self._layer != current.layer
            or self.desired_width != current.desired_width
            or self.desired_height != current.desired_height
        ):
            self.output.organise_layers()
        self.damage()

    def kill(self) -> None:
        self.surface.destroy()

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

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
        self.x = x
        self.y = y
        self._width = int(width)
        self._height = int(height)
        self.surface.configure(self._width, self._height)
        self.damage()

    def cmd_bring_to_front(self) -> None:
        pass


class Internal(_Base, base.Internal):
    """
    Internal windows are simply textures controlled by the compositor.
    """

    def __init__(self, core: Core, qtile: Qtile, x: int, y: int, width: int, height: int):
        self.core = core
        self.qtile = qtile
        self._mapped: bool = False
        self._wid: int = self.core.new_wid()
        self.x: int = x
        self.y: int = y
        self._width: int = width
        self._height: int = height
        self._opacity: float = 1.0
        self._outputs: set[Output] = set(o for o in self.core.outputs if o.contains(self))
        self.texture: Texture = self._new_texture()

    def finalize(self) -> None:
        self.hide()

    def _new_texture(self) -> Texture:
        clear = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, self.width, self.height)
        with cairocffi.Context(clear) as context:
            context.set_source_rgba(0, 0, 0, 0)
            context.paint()

        return Texture.from_pixels(
            self.core.renderer,
            DRM_FORMAT_ARGB8888,
            cairocffi.ImageSurface.format_stride_for_width(cairocffi.FORMAT_ARGB32, self.width),
            self.width,
            self.height,
            cairocffi.cairo.cairo_image_surface_get_data(clear._pointer),
        )

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        """We keep track of which windows are mapped to we know which to render"""
        if mapped == self._mapped:
            return
        self._mapped = mapped
        if mapped:
            self.core.mapped_windows.append(self)
        else:
            self.core.mapped_windows.remove(self)
        self.core.stack_windows()

    def hide(self) -> None:
        self.mapped = False
        self.damage()

    def unhide(self) -> None:
        self.mapped = True
        self.damage()

    def focus(self, warp: bool) -> None:
        self.core.focus_window(self)

    def kill(self) -> None:
        self.hide()
        if self.wid in self.qtile.windows_map:
            # It will be present during config reloads; absent during shutdown as this
            # will follow graceful_shutdown
            del self.qtile.windows_map[self.wid]

    def damage(self) -> None:
        for output in self._outputs:
            output.damage()

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
        if above and self._mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()

        self.x = x
        self.y = y
        needs_reset = width != self.width or height != self.height
        self._width = width
        self._height = height

        if needs_reset:
            self.texture = self._new_texture()

        self._outputs = set(o for o in self.core.outputs if o.contains(self))
        self.damage()

    def info(self) -> dict:
        """Return a dictionary of info."""
        return dict(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )

    def cmd_bring_to_front(self) -> None:
        if self.mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()


WindowType = typing.Union[Window, Static, Internal]


class XdgPopupWindow(HasListeners):
    """
    This represents a single `struct wlr_xdg_popup` object and is owned by a single
    parent window (of `WindowType | XdgPopupWindow`). wlroots does most of the
    work for us, but we need to listen to certain events so that we know when to render
    frames and we need to unconstrain the popups so they are completely visible.
    """

    def __init__(self, parent: XdgWindow | XdgPopupWindow, xdg_popup: XdgPopup):
        self.parent = parent
        self.xdg_popup = xdg_popup
        self.core: Core = parent.core
        self.popups: list[XdgPopupWindow] = []

        # Keep on output
        if isinstance(parent, XdgPopupWindow):
            # This is a nested XdgPopup
            self.output: Output = parent.output
            self.output_box: Box = parent.output_box
        else:
            # Parent is an XdgSurface; This is a first-level XdgPopup
            box = xdg_popup.base.get_geometry()
            lx, ly = self.core.output_layout.closest_point(parent.x + box.x, parent.y + box.y)
            wlr_output = self.core.output_layout.output_at(lx, ly)
            assert wlr_output and isinstance(wlr_output.data, Output)
            self.output = wlr_output.data
            box = Box(*self.output.get_geometry())
            box.x = round(box.x - lx)
            box.y = round(box.y - ly)
            self.output_box = box
        xdg_popup.unconstrain_from_box(self.output_box)

        self.add_listener(xdg_popup.base.map_event, self._on_map)
        self.add_listener(xdg_popup.base.unmap_event, self._on_unmap)
        self.add_listener(xdg_popup.base.destroy_event, self._on_destroy)
        self.add_listener(xdg_popup.base.new_popup_event, self._on_new_popup)
        self.add_listener(xdg_popup.base.surface.commit_event, self._on_commit)

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: popup map")
        self.output.damage()

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: popup unmap")
        self.output.damage()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: popup destroy")
        self.finalize_listeners()
        self.output.damage()

    def _on_new_popup(self, _listener: Listener, xdg_popup: XdgPopup) -> None:
        logger.debug("Signal: popup new_popup")
        self.popups.append(XdgPopupWindow(self, xdg_popup))

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        self.output.damage()


class SubSurface(HasListeners):
    """
    This represents a single `struct wlr_subsurface` object and is owned by a single
    parent window (of `WindowType | SubSurface`). We only need to track them so
    that we can listen to their commit events and render accordingly.
    """

    def __init__(self, parent: XdgWindow | SubSurface, subsurface: WlrSubSurface):
        self.parent = parent
        self.subsurfaces: list[SubSurface] = []

        self.add_listener(subsurface.destroy_event, self._on_destroy)
        self.add_listener(subsurface.surface.commit_event, parent._on_commit)
        self.add_listener(subsurface.surface.new_subsurface_event, self._on_new_subsurface)

    def finalize(self) -> None:
        self.finalize_listeners()
        for subsurface in self.subsurfaces:
            subsurface.finalize()
        self.parent.subsurfaces.remove(self)

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        self.finalize()

    def _on_commit(self, listener: Listener, _data: Any) -> None:
        self.parent._on_commit(listener, None)

    def _on_new_subsurface(self, _listener: Listener, subsurface: WlrSubSurface) -> None:
        self.subsurfaces.append(SubSurface(self, subsurface))


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

        self.add_listener(wlr_constraint.set_region_event, self._on_set_region)
        self.add_listener(wlr_constraint.destroy_event, self._on_destroy)

        owner = None

        if core.qtile and core.qtile.windows_map:
            for win in core.qtile.windows_map.values():
                if isinstance(win, (XdgWindow, XdgStatic)):
                    if win.surface.surface == self.wlr_constraint.surface:
                        owner = win
                        break

        if owner is None:
            logger.error("No window found for pointer constraints. Please report.")
            raise RuntimeError

        self.window: XdgWindow | XdgStatic = owner

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
