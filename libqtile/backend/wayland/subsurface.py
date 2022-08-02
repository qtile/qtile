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

from libqtile.backend.wayland.wlrq import HasListeners

if typing.TYPE_CHECKING:
    from typing import Any

    from wlroots.wlr_types.surface import SubSurface as WlrSubSurface

    from libqtile.backend.wayland.xdgwindow import XdgWindow


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
