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

from libqtile.backend import base
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from wlroots.wlr_types import xdg_shell

    from libqtile.backend.wayland.core import Core


class Window(base.Window):
    def __init__(self, core: Core, surface: xdg_shell.XdgSurface, wid: int):
        base.Window.__init__(self)
        self.core = core
        self.surface = surface
        self._wid = wid
        self._group = 0
        self.mapped = False
        self.x = 10
        self.y = 10

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
        self.core.windows.remove(self)

    @property
    def wid(self):
        return self._wid

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

    def _on_destroy(self, _listener, data):
        logger.debug("Signal: window destroy")
        self.finalize()

    def _on_request_fullscreen(self, _listener, data: xdg_shell.XdgTopLevelSetFullscreenEvent):
        logger.debug("Signal: window request_fullscreen")
        # TODO

    def hide(self):
        self.surface.unmap_event.emit()

    def unhide(self):
        self.surface.map_event.emit()
