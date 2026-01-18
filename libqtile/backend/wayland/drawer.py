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

        scale = self._win.scale

        # Paint recorded operations to our window's underlying ImageSurface
        # Allocation could have failed or surface may have been destroyed, NULL check
        if not self._win.surface:
            return
        surface = cairocffi.Surface._from_pointer(self._win.surface, True)  # type: ignore[attr-defined]
        with cairocffi.Context(surface) as context:
            context.set_operator(cairocffi.OPERATOR_SOURCE)
            # Scale the cairo surface by its output (display) scale
            context.scale(scale, scale)
            # Adjust the source surface position by src_x and src_y e.g. if we want
            # to render part of the surface in a different position
            context.set_source_surface(self.surface, offsetx - src_x, offsety - src_y)
            context.rectangle(offsetx, offsety, width, height)
            context.fill()

        self._win.set_buffer_with_damage(offsetx, offsety, width, height)
