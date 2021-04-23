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

import functools
import typing

from pywayland.server import Listener
from wlroots import ffi
from wlroots.util.edges import Edges

from libqtile import hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Dict, Optional, Tuple

    from wlroots.wlr_types import xdg_shell

    from libqtile.backend.wayland.core import Core
    from libqtile.core.manager import Qtile

EDGES_TILED = Edges.TOP | Edges.BOTTOM | Edges.LEFT | Edges.RIGHT
EDGES_FLOAT = Edges.NONE


@functools.lru_cache()
def _rgb(color) -> ffi.CData:
    """Helper to create and cache float[4] arrays for border painting"""
    if isinstance(color, ffi.CData):
        return color
    return ffi.new("float[4]", utils.rgb(color))


class Window(base.Window):
    def __init__(self, core: Core, qtile: Qtile, surface: xdg_shell.XdgSurface, wid: int):
        base.Window.__init__(self)
        self.core = core
        self.qtile = qtile
        self.surface = surface
        self._wid = wid
        self._group = 0
        self.mapped = False
        self.x = 0
        self.y = 0
        self.borderwidth: int = 0
        self.bordercolor: ffi.CData = _rgb((0, 0, 0, 1))
        self.opacity: float = 1.0

        self.surface.set_tiled(EDGES_TILED)
        self._float_state = FloatStates.NOT_FLOATING
        self.float_x = self.x
        self.float_y = self.y
        self.float_width = self.width
        self.float_height = self.height

        self._on_map_listener = Listener(self._on_map)
        self._on_unmap_listener = Listener(self._on_unmap)
        self._on_destroy_listener = Listener(self._on_destroy)
        self._on_request_fullscreen_listener = Listener(self._on_request_fullscreen)
        surface.map_event.add(self._on_map_listener)
        surface.unmap_event.add(self._on_unmap_listener)
        surface.destroy_event.add(self._on_destroy_listener)
        surface.toplevel.request_fullscreen_event.add(self._on_request_fullscreen_listener)

    def finalize(self):
        self._on_map_listener.remove()
        self._on_unmap_listener.remove()
        self._on_destroy_listener.remove()
        self._on_request_fullscreen_listener.remove()
        self.core.flush()

    @property
    def wid(self):
        return self._wid

    @property
    def width(self):
        return self.surface.surface.current.width

    @property
    def height(self):
        return self.surface.surface.current.height

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, index):
        self._group = index

    def _on_map(self, _listener, data):
        logger.debug("Signal: window map")
        self.mapped = True
        self.core.focus_window(self)

    def _on_unmap(self, _listener, data):
        logger.debug("Signal: window unmap")
        self.mapped = False
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            self.core.seat.keyboard_clear_focus()

    def _on_destroy(self, _listener, data):
        logger.debug("Signal: window destroy")
        self.qtile.unmanage(self.wid)
        self.finalize()

    def _on_request_fullscreen(self, _listener, event: xdg_shell.XdgTopLevelSetFullscreenEvent):
        logger.debug("Signal: window request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            self.fullscreen = event.fullscreen

    def hide(self):
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self):
        if not self.mapped:
            self.surface.map_event.emit()

    def kill(self):
        self.surface.send_close()

    def get_wm_class(self) -> Optional[str]:
        # TODO
        return None

    def paint_borders(self, color, width) -> None:
        self.bordercolor = _rgb(color)
        self.borderwidth = width

    @property
    def floating(self):
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                self._enablefloating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self.float_width,
                    self.float_height
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self.float_width = self.width
                self.float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')

    @property
    def fullscreen(self):
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        if do_full:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)
            self._enablefloating(
                screen.x,
                screen.y,
                screen.width,
                screen.height,
                new_float_state=FloatStates.FULLSCREEN
            )
            return

        if self._float_state == FloatStates.FULLSCREEN:
            self.floating = False

    @property
    def maximized(self):
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)

            self._enablefloating(
                screen.dx,
                screen.dy,
                screen.dwidth,
                screen.dheight,
                new_float_state=FloatStates.MAXIMIZED
            )
        else:
            if self._float_state == FloatStates.MAXIMIZED:
                self.floating = False

    @property
    def minimized(self):
        return self._float_state == FloatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != FloatStates.MINIMIZED:
                self._enablefloating(new_float_state=FloatStates.MINIMIZED)
        else:
            if self._float_state == FloatStates.MINIMIZED:
                self.floating = False

    def focus(self, warp):
        self.core.focus_window(self)
        if warp:
            self.core.warp_pointer(self.x + self.width, self.y + self.height)

    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None):

        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        self.x = x
        self.y = y
        self.surface.set_size(width, height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            # TODO when general z-axis control is implemented
            pass

    def _tweak_float(self, x=None, y=None, dx=0, dy=0, w=None, h=None, dw=0, dh=0):
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

        screen = self.qtile.find_closest_screen(
            self.x + self.width // 2, self.y + self.height // 2
        )
        if self.group and screen is not None and screen != self.group.screen:
            self.group.remove(self, force=True)
            screen.group.add(self, force=True)
            self.qtile.focus_screen(screen.index)

        self._reconfigure_floating(x, y, w, h)

    def _enablefloating(self, x=None, y=None, w=None, h=None,
                        new_float_state=FloatStates.FLOATING):
        self._reconfigure_floating(x, y, w, h, new_float_state)

    def _reconfigure_floating(self, x, y, w, h, new_float_state=FloatStates.FLOATING):
        if new_float_state == FloatStates.MINIMIZED:
            self.hide()
        else:
            # TODO: Can we get min/max size, resizing increments etc and respect them?
            self.place(
                x, y, w, h, self.borderwidth, self.bordercolor, above=True,
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire('float_change')

    def cmd_focus(self, warp=None):
        """Focuses the window."""
        if warp is None:
            warp = self.qtile.config.cursor_warp
        self.focus(warp=warp)

    def cmd_info(self) -> Dict:
        """Return a dictionary of info."""
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            group=self.group.name if self.group else None,
            id=self.wid,
            floating=self._float_state != FloatStates.NOT_FLOATING,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN
        )

    def cmd_move_floating(self, dx: int, dy: int) -> None:
        self._tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw: int, dh: int) -> None:
        self._tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x: int, y: int) -> None:
        self._tweak_float(x=x, y=y)

    def cmd_set_size_floating(self, w: int, h: int) -> None:
        self._tweak_float(w=w, h=h)

    def cmd_place(self, x, y, width, height, borderwidth, bordercolor,
                  above=False, margin=None):
        self.place(x, y, width, height, borderwidth, bordercolor, above,
                   margin)

    def cmd_get_position(self) -> Tuple[int, int]:
        return self.x, self.y

    def cmd_get_size(self) -> Tuple[int, int]:
        return self.width, self.height

    def cmd_toggle_floating(self) -> None:
        self.floating = not self.floating

    def cmd_enable_floating(self):
        self.floating = True

    def cmd_disable_floating(self):
        self.floating = False

    def cmd_toggle_maximize(self) -> None:
        self.maximized = not self.maximized

    def cmd_toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    def cmd_enable_fullscreen(self) -> None:
        self.fullscreen = True

    def cmd_disable_fullscreen(self) -> None:
        self.fullscreen = False

    def cmd_bring_to_front(self) -> None:
        # TODO
        pass


class Internal(Window, base.Internal):
    pass


class Static(Window, base.Static):
    pass


WindowType = typing.Union[Window, Internal, Static]
