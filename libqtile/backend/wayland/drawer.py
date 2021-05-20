from __future__ import annotations

import math
from typing import TYPE_CHECKING

import cairocffi

from libqtile.backend import base

if TYPE_CHECKING:
    from typing import Optional

    from libqtile.backend.wayland.window import Internal
    from libqtile.core.manager import Qtile


class Drawer(base.Drawer):
    """A helper class for drawing and text layout."""
    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        base.Drawer.__init__(self, qtile, win, width, height)
        self._target = win.image_surface
        self._texture = win.texture
        self._stride = self._target.format_stride_for_width(
            cairocffi.FORMAT_ARGB32, self.width
        )

        for output in qtile.core.outputs:  # type: ignore
            if output.contains(win):
                break  # Internals only show on one output
        self._output = output

    def paint_to(self, drawer):
        drawer.ctx.set_source_surface(self._target)
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
        with cairocffi.Context(self._target) as context:
            context.set_source_surface(self.surface, offsetx, offsety)
            context.paint()

        # Copy drawn ImageSurface data into rendered wlr_texture
        self._texture.write_pixels(
            self._stride,
            width,
            height,
            cairocffi.cairo.cairo_image_surface_get_data(self._target._pointer),
            src_x=offsetx,
            src_y=offsety,
            dst_x=offsetx,
            dst_y=offsety,
        )
        self._output.damage.add_whole()

        # Clear RecordingSurface of operations
        self._reset_surface()
