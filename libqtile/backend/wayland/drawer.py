from __future__ import annotations

from typing import TYPE_CHECKING

import cairocffi

from libqtile import utils
from libqtile.backend import base

if TYPE_CHECKING:
    from libqtile.backend.wayland.window import Internal
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType


class Drawer(base.Drawer):
    """
    A helper class for drawing and text layout.

    1. We stage drawing operations locally in memory using a cairo RecordingSurface.
    2. Then apply these operations to our ImageSurface self._source.
    3. Then copy the pixels onto the window's wlr_texture.
    """

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        base.Drawer.__init__(self, qtile, win, width, height)

        self._stride = cairocffi.ImageSurface.format_stride_for_width(
            cairocffi.FORMAT_ARGB32, self.width
        )
        self._source = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
        with cairocffi.Context(self._source) as context:
            # Initialise surface to all black
            context.set_source_rgba(*utils.rgb("#000000"))
            context.paint()

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        if offsetx > self._win.width:  # type: ignore
            return

        # We need to set the current draw area so we can compare to the previous one
        self.current_rect = (offsetx, offsety, width, height)
        # rect_changed = current_rect != self.previous_rect

        if not self.needs_update:
            return

        # Keep track of latest rect covered by this drawwer
        self.previous_rect = self.current_rect

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
        self._win.texture.write_pixels(  # type: ignore
            self._stride,
            width,
            height,
            cairocffi.cairo.cairo_image_surface_get_data(self._source._pointer),
            dst_x=offsetx,
            dst_y=offsety,
        )
        self._win.damage()  # type: ignore

    def clear(self, colour: ColorsType) -> None:
        # Draw background straight to ImageSurface
        ctx = cairocffi.Context(self._source)
        ctx.save()
        ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.set_source_rgb(colour, ctx=ctx)
        ctx.paint()
        ctx.restore()
