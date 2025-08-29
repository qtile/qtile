# Copyright (c) 2022 m-col
# Copyright (c) 2023 elParaguayo
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

from typing import TYPE_CHECKING

import cairocffi

from libqtile.backend.base import drawer

if TYPE_CHECKING:
    from libqtile.backend.wayland.window import Internal
    from libqtile.core.manager import Qtile


class Drawer(drawer.Drawer):
    """
    A helper class for drawing and text layout.

    1. We stage drawing operations locally in memory using a cairo RecordingSurface.
    2. Then apply these operations to the windows's underlying ImageSurface.
    """

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        drawer.Drawer.__init__(self, qtile, win, width, height)

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
        src_x: int = 0,
        src_y: int = 0,
    ) -> None:
        if offsetx > self._win.width:
            return

        # Make sure geometry doesn't extend beyond texture
        if width is None:
            width = self.width
        if width > self._win.width - offsetx:
            width = self._win.width - offsetx
        if height is None:
            height = self.height
        if height > self._win.height - offsety:
            height = self._win.height - offsety

        # Paint recorded operations to our window's underlying ImageSurface
        # Allocation could have failed, NULL check
        if not self._win.surface:
            return
        surface = cairocffi.Surface._from_pointer(self._win.surface, True) # type: ignore[attr-defined]
        with cairocffi.Context(surface) as context:
            context.set_operator(cairocffi.OPERATOR_SOURCE)
            # Adjust the source surface position by src_x and src_y e.g. if we want
            # to render part of the surface in a different position
            context.set_source_surface(self.surface, offsetx - src_x, offsety - src_y)
            context.rectangle(offsetx, offsety, width, height)
            context.fill()

        self._win.set_buffer_with_damage(offsetx, offsety, width, height)
