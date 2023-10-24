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

import typing

from pywayland.server import Listener
from wlroots.util.clock import Timespec
from wlroots.util.edges import Edges
from wlroots.wlr_types.xdg_shell import XdgSurface, XdgTopLevelWMCapabilities

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.window import Static, Window
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    pass

if typing.TYPE_CHECKING:
    from typing import Any

    from libqtile.backend.wayland.core import Core
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType

EDGES_TILED = Edges.TOP | Edges.BOTTOM | Edges.LEFT | Edges.RIGHT
WM_CAPABILITIES = (
    XdgTopLevelWMCapabilities.MAXIMIZE
    | XdgTopLevelWMCapabilities.FULLSCREEN
    | XdgTopLevelWMCapabilities.MINIMIZE
)


class XdgWindow(Window[XdgSurface]):
    """An Wayland client connecting via the xdg shell."""

    def __init__(self, core: Core, qtile: Qtile, surface: XdgSurface):
        Window.__init__(self, core, qtile, surface)

        self._wm_class = surface.toplevel.app_id
        surface.set_wm_capabilities(WM_CAPABILITIES)
        surface.data = self.data_handle
        self.tree = core.scene.xdg_surface_create(self.container, surface)

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.toplevel.request_maximize_event, self._on_request_maximize)
        self.add_listener(surface.toplevel.request_fullscreen_event, self._on_request_fullscreen)

        self.ftm_handle = core.foreign_toplevel_manager_v1.create_handle()

    def _on_request_fullscreen(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            requested = self.surface.toplevel.requested.fullscreen
            if self.fullscreen == requested:
                self.surface.schedule_configure()
            else:
                self.fullscreen = requested
        else:
            # Per xdg-shell protocol we must send a configure in response to this
            # request. Since we're ignoring it, we must schedule a configure manually.
            self.surface.schedule_configure()

    def _on_request_maximize(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow request_maximize")
        self.maximized = self.surface.toplevel.requested.maximized

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow set_title")
        title = self.surface.toplevel.title
        if title and title != self.name:
            self.name = title
            if self.ftm_handle:
                self.ftm_handle.set_title(self.name)
            hook.fire("client_name_updated", self)

    def _on_set_app_id(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow set_app_id")
        self._wm_class = self.surface.toplevel.app_id
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def unhide(self) -> None:
        self._wm_class = self.surface.toplevel.app_id

        if self not in self.core.pending_windows:
            # Regular usage
            if not self.container.node.enabled and self.group and self.group.screen:
                self.container.node.set_enabled(enabled=True)
            return

        # This is the first time this window has mapped, so we need to do some initial
        # setup.
        self.core.pending_windows.remove(self)
        self._wid = self.core.new_wid()
        logger.debug(
            "Managing new top-level window with window ID: %s, app_id: %s",
            self._wid,
            self._wm_class,
        )

        # Save the client's desired geometry
        surface = self.surface
        geometry = surface.get_geometry()
        self._width = self._float_width = geometry.width
        self._height = self._float_height = geometry.height

        # Tell the client to render tiled edges
        surface.set_tiled(EDGES_TILED)

        handle = self.ftm_handle
        assert handle is not None

        # Get the client's name
        if surface.toplevel.title:
            self.name = surface.toplevel.title
            handle.set_title(self.name)
        if self._wm_class:
            handle.set_app_id(self._wm_class or "")

        # Add the toplevel's listeners
        self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
        self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)
        self.add_listener(handle.request_maximize_event, self._on_foreign_request_maximize)
        self.add_listener(handle.request_minimize_event, self._on_foreign_request_minimize)
        self.add_listener(handle.request_activate_event, self._on_foreign_request_activate)
        self.add_listener(handle.request_fullscreen_event, self._on_foreign_request_fullscreen)
        self.add_listener(handle.request_close_event, self._on_foreign_request_close)

        self.qtile.manage(self)

        # Send a frame done event to provide an opportunity to redraw even if we aren't
        # going to map (i.e. because the window was opened on a hidden group)
        surface.surface.send_frame_done(Timespec.get_monotonic_time())

    @expose_command()
    def kill(self) -> None:
        self.surface.send_close()

    def has_fixed_size(self) -> bool:
        state = self.surface.toplevel._ptr.current
        return 0 < state.min_width == state.max_width and 0 < state.min_height == state.max_height

    def is_transient_for(self) -> base.WindowType | None:
        """What window is this window a transient window for?"""
        if parent := self.surface.toplevel.parent:
            for win in self.qtile.windows_map.values():
                if isinstance(win, XdgWindow) and win.surface.toplevel == parent:
                    return win
        return None

    def get_pid(self) -> int:
        pid = ffi.new("pid_t *")
        lib.wl_client_get_credentials(self.surface._ptr.client.client, pid, ffi.NULL, ffi.NULL)
        return pid[0]

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self.surface.set_fullscreen(do_full)
            if self.ftm_handle:
                self.ftm_handle.set_fullscreen(do_full)

    def handle_activation_request(self, focus_on_window_activation: str) -> None:
        """Respond to XDG activation requests targeting this window."""
        assert self.qtile is not None

        if self.group is None:
            # Likely still pending, ignore this request.
            return

        if focus_on_window_activation == "focus":
            logger.debug("Focusing window (focus_on_window_activation='focus')")
            self.qtile.current_screen.set_group(self.group)
            self.group.focus(self)

        elif focus_on_window_activation == "smart":
            if not self.group.screen:
                logger.debug("Ignoring focus request (focus_on_window_activation='smart')")
            elif self.group.screen == self.qtile.current_screen:
                logger.debug("Focusing window (focus_on_window_activation='smart')")
                self.qtile.current_screen.set_group(self.group)
                self.group.focus(self)
            else:
                self._urgent = True
                hook.fire("client_urgent_hint_changed", self)

        elif focus_on_window_activation == "urgent":
            self._urgent = True
            hook.fire("client_urgent_hint_changed", self)

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
        self.container.node.set_position(x, y)
        self._width = width
        self._height = height
        self.surface.set_size(width, height)
        self.surface.set_bounds(width, height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.bring_to_front()

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        Window.static(self, screen, x, y, width, height)
        win = typing.cast(XdgStatic, self.qtile.windows_map[self._wid])

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.window = win

        hook.fire("client_managed", win)

    def _to_static(self, x: int | None, y: int | None, width: int | None, height: int | None) -> XdgStatic:
        return XdgStatic(
            self.core,
            self.qtile,
            self,
            self._idle_inhibitors_count,
        )


class XdgStatic(Static[XdgSurface]):
    """A static window belonging to the XDG shell."""

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        win: XdgWindow,
        idle_inhibitor_count: int,
    ):
        surface = win.surface
        Static.__init__(
            self, core, qtile, surface, win.wid, idle_inhibitor_count=idle_inhibitor_count
        )

        if surface.toplevel.title:
            self.name = surface.toplevel.title
        self._wm_class = surface.toplevel.app_id

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        # self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
        self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)

        # Take control of the scene tree
        self.container = win.container
        self.container.node.data = self.data_handle
        self.tree = win.tree

    @expose_command()
    def kill(self) -> None:
        self.surface.send_close()

    def hide(self) -> None:
        super().hide()
        self.container.node.set_enabled(enabled=False)

    def unhide(self) -> None:
        self.container.node.set_enabled(enabled=True)

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
        self.surface.set_size(width, height)
        self.surface.set_bounds(width, height)
        self.container.node.set_position(x, y)

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgstatic set_title")
        title = self.surface.toplevel.title
        if title and title != self.name:
            self.name = title
            if self.ftm_handle:
                self.ftm_handle.set_title(self.name)
            hook.fire("client_name_updated", self)

    def _on_set_app_id(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgstatic set_app_id")
        self._wm_class = self.surface.toplevel.app_id
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")
