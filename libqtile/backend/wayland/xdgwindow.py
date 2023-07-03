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

from pywayland import ffi as wlffi
from pywayland import lib as wllib
from pywayland.server import Listener
from wlroots import ffi
from wlroots.util.box import Box
from wlroots.util.clock import Timespec
from wlroots.util.edges import Edges
from wlroots.wlr_types.xdg_shell import XdgPopup, XdgSurface, XdgTopLevelSetFullscreenEvent

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.subsurface import SubSurface
from libqtile.backend.wayland.window import Static, Window
from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

    from wlroots.wlr_types.surface import SubSurface as WlrSubSurface

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.output import Output
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType

EDGES_TILED = Edges.TOP | Edges.BOTTOM | Edges.LEFT | Edges.RIGHT


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
        self.add_listener(surface.toplevel.request_fullscreen_event, self._on_request_fullscreen)

        surface.data = self.ftm_handle = core.foreign_toplevel_manager_v1.create_handle()

    def finalize(self) -> None:
        Window.finalize(self)
        for subsurface in self.subsurfaces:
            subsurface.finalize()

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow map")

        if not self._wm_class == self.surface.toplevel.app_id:
            self._wm_class = self.surface.toplevel.app_id

        if self in self.core.pending_windows:
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

            assert self.ftm_handle is not None

            # Get the client's name
            if surface.toplevel.title:
                self.name = surface.toplevel.title
                self.ftm_handle.set_title(self.name)
            if self._wm_class:
                self.ftm_handle.set_app_id(self._wm_class or "")

            # Add the toplevel's listeners
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

            # Send a frame done event to provide an opportunity to redraw even if we
            # aren't going to map (i.e. because the window was opened on a hidden group)
            surface.surface.send_frame_done(Timespec.get_monotonic_time())

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
            if self.ftm_handle:
                self.ftm_handle.set_title(self.name)
            hook.fire("client_name_updated", self)

    def _on_set_app_id(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xdgwindow set_app_id")
        self._wm_class = self.surface.toplevel.app_id
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

    @expose_command()
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
        pid = wlffi.new("pid_t *")
        wllib.wl_client_get_credentials(self.surface._ptr.client.client, pid, ffi.NULL, ffi.NULL)
        return pid[0]

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self.surface.set_fullscreen(do_full)
            if self.ftm_handle:
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

        if self.ftm_handle:
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
        self._width = width
        self._height = height
        self.surface.set_size(width, height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.bring_to_front()

        prev_outputs = self._outputs.copy()
        self._find_outputs()
        for output in self._outputs | prev_outputs:
            output.damage()

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
        win = self.qtile.windows_map[self._wid]
        assert isinstance(win, XdgStatic)
        win.subsurfaces = self.subsurfaces

        for pc in self.core.pointer_constraints.copy():
            if pc.window is self:
                pc.window = win

        hook.fire("client_managed", win)

    def _to_static(self) -> XdgStatic:
        return XdgStatic(
            self.core, self.qtile, self.surface, self.wid, self._idle_inhibitors_count
        )


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

    @expose_command()
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
        self.surface.set_size(width, height)
        self.paint_borders(bordercolor, borderwidth)
        self._find_outputs()
        self.damage()

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
            if wlr_output and wlr_output.data:
                output = wlr_output.data
            else:
                logger.warning("Failed to find output at for xdg_popup. Please report.")
                output = self.core.outputs[0]
            self.output = output
            box = Box(*output.get_geometry())
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
