from __future__ import annotations

import math
from typing import TYPE_CHECKING

import cairocffi

from libqtile import utils
from libqtile.backend import base

if TYPE_CHECKING:
    from typing import Optional

    from libqtile.backend.wayland.window import Internal
    from libqtile.core.manager import Qtile


class Drawer(base.Drawer):
    """
    A helper class for drawing and text layout.

    1. We stage drawing operations locally in memory using a cairo RecordingSurface.
    2. Then apply these operations to our ImageSurface self._source
    3. Then copy the pixels onto the wlr_texture self._target
    """
    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        base.Drawer.__init__(self, qtile, win, width, height)

        self._target = win.texture
        self._stride = cairocffi.ImageSurface.format_stride_for_width(
            cairocffi.FORMAT_ARGB32, self.width
        )
        self._source = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
        with cairocffi.Context(self._source) as context:
            # Initialise surface to all black
            context.set_source_rgba(*utils.rgb("#000000"))
            context.paint()

        for output in qtile.core.outputs:  # type: ignore
            if output.contains(win):
                break  # Internals only show on one output
        self._output = output

    def paint_to(self, drawer):
        drawer.ctx.set_source_surface(self._source)
        drawer.ctx.paint()

    def draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        if offsetx > self._win.width:  # type: ignore
            return

        # Only attempt to run RecordingSurface's operations if it actually has
        # some. self.surface.ink_extents() computes the bounds of the current
        # list of operations. If any of the bounds are not 0.0 then the surface
        # has operations and we should paint them.
        if not any(not math.isclose(0.0, i) for i in self.surface.ink_extents()):
            return

        # Make sure geometry doesn't extend beyond texture
        if width is None:
            width = self.width
        if width > self._win.width - offsetx:  # type: ignore
            width = self._win.width - offsetx  # type: ignore
        if height is None:
            height = self.height
        if height > self._win.height - offsety:  # type: ignore
            height = self._win.height - offsety  # type: ignore

        # Paint RecordingSurface operations our window's ImageSurface
        with cairocffi.Context(self._source) as context:
            context.set_source_surface(self.surface)
            context.paint()

        # Copy drawn ImageSurface data into rendered wlr_texture
        self._target.write_pixels(
            self._stride,
            width,  # type: ignore
            height,  # type: ignore
            cairocffi.cairo.cairo_image_surface_get_data(self._source._pointer),
            dst_x=offsetx,
            dst_y=offsety,
        )
        self._output.damage.add_whole()

        # Clear RecordingSurface of operations
        self._reset_surface()
