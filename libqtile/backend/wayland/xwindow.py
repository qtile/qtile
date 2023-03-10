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

from wlroots import xwayland

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.window import Static, Window
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

    import wlroots.wlr_types.foreign_toplevel_management_v1 as ftm
    from pywayland.server import Listener

    from libqtile.backend.wayland.core import Core
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType


class XWindow(Window[xwayland.Surface]):
    """An X11 client connecting via XWayland."""

    def __init__(self, core: Core, qtile: Qtile, surface: xwayland.Surface):
        Window.__init__(self, core, qtile, surface)

        self._wm_class = self.surface.wm_class
        self._unmapping: bool = False  # Whether the client or Qtile unmapped this

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        """XWindows also need to restack in the X server's Z stack."""
        if mapped != self._mapped:
            if mapped:
                self.surface.restack(None, 0)  # XCB_STACK_MODE_ABOVE
            Window.mapped.fset(self, mapped)  # type: ignore

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow map")

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
            self._wid = self.core.new_wid()
            logger.debug("Managing new XWayland window with window ID: %s", self._wid)
            surface = self.surface

            # Make it static if it isn't a regular window
            if surface.override_redirect:
                self.static(None, surface.x, surface.y, surface.width, surface.height)
                win = self.qtile.windows_map[self._wid]
                assert isinstance(win, XStatic)
                self.core.focus_window(win)
                return

            # Save the client's desired geometry. xterm seems to have these set to 1, so
            # let's ignore 1 or below. The float sizes will be fetched when it is floated.
            if surface.width > 1:
                self._width = self._float_width = surface.width
            if self.surface.height > 1:
                self._height = self._float_height = surface.height

            surface.data = self.ftm_handle = self.core.foreign_toplevel_manager_v1.create_handle()
            # Get the client's name and class
            title = surface.title
            if title:
                self.name = title
                self.ftm_handle.set_title(self.name)
            self._wm_class = surface.wm_class
            self.ftm_handle.set_app_id(self._wm_class or "")

            # Add event listeners
            self.add_listener(surface.surface.commit_event, self._on_commit)
            self.add_listener(surface.request_fullscreen_event, self._on_request_fullscreen)
            self.add_listener(surface.set_title_event, self._on_set_title)
            self.add_listener(surface.set_class_event, self._on_set_class)
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
            # Client unmapped X11 windows return to a pending state, where we don't
            # manage them, but clients can re-use them.
            self.qtile.unmanage(self.wid)
            self.finalize()
            self.add_listener(self.surface.map_event, self._on_map)
            self.add_listener(self.surface.unmap_event, self._on_unmap)
            self.add_listener(self.surface.destroy_event, self._on_destroy)
            self.core.pending_windows.add(self)
            self._wid = -1

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
            if self.ftm_handle:
                self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow set_class")
        self._wm_class = self.surface.wm_class
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def hide(self) -> None:
        if self.mapped:
            self._unmapping = True
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

    @expose_command()
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
        self._width = width
        self._height = height
        self.surface.configure(x, y, width, height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.bring_to_front()

        prev_outputs = self._outputs.copy()
        self._find_outputs()
        for output in self._outputs | prev_outputs:
            output.damage()

    @expose_command()
    def bring_to_front(self) -> None:
        if self.mapped:
            self.core.stack_windows(restack=self)
            self.surface.restack(None, 0)  # XCB_STACK_MODE_ABOVE

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
        hook.fire("client_managed", self.qtile.windows_map[self._wid])

    def _to_static(self) -> XStatic:
        return XStatic(self.core, self.qtile, self.surface, self.wid, self._idle_inhibitors_count)


class XStatic(Static[xwayland.Surface]):
    """A static window belonging to the XWayland shell."""

    surface: xwayland.Surface

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

        # Checks to see if the user manually created the XStatic surface.
        # In which case override_redirect would be false.
        if surface.override_redirect:
            self.add_listener(surface.set_geometry_event, self._on_set_geometry)

        self.ftm_handle: ftm.ForeignToplevelHandleV1 | None = None

    @expose_command()
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
            if self.ftm_handle:
                self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_class")
        self._wm_class = self.surface.wm_class
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def _on_set_geometry(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_geometry")
        self.place(
            self.surface.x, self.surface.y, self.surface.width, self.surface.height, 0, None
        )
