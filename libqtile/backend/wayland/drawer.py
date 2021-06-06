from __future__ import annotations

import math
from typing import TYPE_CHECKING

import cairocffi

from libqtile import utils
from libqtile.backend import base

if TYPE_CHECKING:
    from typing import Optional, Tuple

    from libqtile.backend.wayland.window import Internal
    from libqtile.core.manager import Qtile


class Drawer(base.Drawer):
    """
    A helper class for drawing and text layout.

    1. We stage drawing operations locally in memory using a cairo RecordingSurface.
    2. Then apply these operations to our ImageSurface self._source
    3. Then copy the pixels onto the wlr_texture self._target
    """

    # We need to track extent of drawing to know when to redraw.
    previous_rect: Tuple[int, int, Optional[int], Optional[int]]

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

        self.previous_rect = (-1, -1, -1, -1)

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

        # We can't test for the surface's ink_extents here on its own as a completely
        # transparent background would not show any extents but we may still need to
        # redraw (e.g. if a Spacer widget has changed position and/or size)

        # Check if current rect has changed since previous draw
        current_rect = (offsetx, offsety, width, height)
        rect_changed = current_rect != self.previous_rect

        # Check if draw has content (would be False for completely transparent drawer)
        ink_changed = any(not math.isclose(0.0, i) for i in self.surface.ink_extents())

        if not ink_changed and not rect_changed:
            return

        # Keep track of latest rect covered by this drawwer
        self.previous_rect = current_rect

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
        self._win.damage()  # type: ignore

        # Clear RecordingSurface of operations
        self._reset_surface()

    def clear(self, colour):
        # Some hacks needed for transparency

        # Check if any colour is not fully opaque
        if utils.has_transparency(colour):

            # RecordingSurface won't write clear operation to surface so we
            # need to clear that surface directly.
            if getattr(self, "_source", None) is not None:
                ctx = cairocffi.Context(self._source)
                ctx.save()
                ctx.set_operator(cairocffi.OPERATOR_CLEAR)
                ctx.paint()
                ctx.restore()

        self.ctx.save()
        self.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.set_source_rgb(colour)
        self.ctx.paint()
        self.ctx.restore()
