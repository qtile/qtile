from __future__ import annotations

import math
from typing import TYPE_CHECKING

import cairocffi
import xcffib.xproto

from libqtile import utils
from libqtile.backend import base

if TYPE_CHECKING:
    from typing import Optional

    from libqtile.backend.base import Internal
    from libqtile.core.manager import Qtile


class Drawer(base.Drawer):
    """A helper class for drawing to Internal windows.

    The underlying surface here is an XCBSurface backed by a pixmap. We draw to the
    pixmap starting at offset 0, 0, and when the time comes to display to the window (on
    draw()), we copy the appropriate portion of the pixmap onto the window. In the event
    that our drawing area is resized, we invalidate the underlying surface and pixmap
    and recreate them when we need them again with the new geometry.
    """
    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        base.Drawer.__init__(self, qtile, win, width, height)
        self._xcb_surface = None
        self._pixmap = None
        self._gc = None

    def finalize(self):
        self._free_xcb_surface()
        self._free_pixmap()
        self._free_gc()
        base.Drawer.finalize(self)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > self._width:
            self._free_xcb_surface()
            self._free_pixmap()
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        if height > self._height:
            self._free_xcb_surface()
            self._free_pixmap()
        self._height = height

    @property
    def pixmap(self):
        if self._pixmap is None:
            # draw here since the only use case of this function is in the
            # systray widget which expects a filled pixmap.
            self.draw()
        return self._pixmap

    def _create_gc(self):
        gc = self.qtile.core.conn.conn.generate_id()
        self.qtile.core.conn.conn.core.CreateGC(
            gc,
            self._win.wid,
            xcffib.xproto.GC.Foreground | xcffib.xproto.GC.Background,
            [
                self.qtile.core.conn.default_screen.black_pixel,
                self.qtile.core.conn.default_screen.white_pixel,
            ],
        )
        return gc

    def _free_gc(self):
        if self._gc is not None:
            self.qtile.core.conn.conn.core.FreeGC(self._gc)
            self._gc = None

    def _create_xcb_surface(self):
        surface = cairocffi.XCBSurface(
            self.qtile.core.conn.conn,
            self._pixmap,
            self.qtile.core.conn.default_screen.default_visual,
            self.width,
            self.height,
        )
        return surface

    def _free_xcb_surface(self):
        if self._xcb_surface is not None:
            self._xcb_surface.finish()
            self._xcb_surface = None

    def _create_pixmap(self):
        pixmap = self.qtile.core.conn.conn.generate_id()
        self.qtile.core.conn.conn.core.CreatePixmap(
            self.qtile.core.conn.default_screen.default_depth,
            pixmap,
            self._win.wid,
            self.width,
            self.height,
        )
        return pixmap

    def _free_pixmap(self):
        if self._pixmap is not None:
            self.qtile.core.conn.conn.core.FreePixmap(self._pixmap)
            self._pixmap = None

    def paint_to(self, drawer):
        # If XCBSurface has been invalidated, we need to draw now to create it
        if self._xcb_surface is None:
            self.draw()
        drawer.ctx.set_source_surface(self._xcb_surface)
        drawer.ctx.paint()

    def _paint(self):
        # Only attempt to run RecordingSurface's operations if it actually has
        # some. self.surface.ink_extents() computes the bounds of the current
        # list of operations. If any of the bounds are not 0.0 then the surface
        # has operations and we should paint them.
        if any(not math.isclose(0.0, i) for i in self.surface.ink_extents()):
            # Paint RecordingSurface operations to the XCBSurface
            ctx = cairocffi.Context(self._xcb_surface)
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.paint()

            # Clear RecordingSurface of operations
            self._reset_surface()

    def draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        # If this is our first draw, create the gc
        if self._gc is None:
            self._gc = self._create_gc()

        # If the Drawer has been resized/invalidated we need to recreate these
        if self._xcb_surface is None:
            self._pixmap = self._create_pixmap()
            self._xcb_surface = self._create_xcb_surface()

        # paint stored operations(if any) to XCBSurface
        self._paint()

        # Finally, copy XCBSurface's underlying pixmap to the window.
        self.qtile.core.conn.conn.core.CopyArea(  # type: ignore
            self._pixmap,
            self._win.wid,
            self._gc,
            0, 0,  # srcx, srcy
            offsetx, offsety,  # dstx, dsty
            self.width if width is None else width,
            self.height if height is None else height
        )

    def _find_root_visual(self):
        for i in self.qtile.core.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.core.conn.default_screen.root_visual:
                    return v

    def clear(self, colour):
        # If the drawer is 32 bit then we need to do some extra work to clear it
        # before drawing semi-opaque content
        if utils.has_transparency(colour) and self.qtile.core.conn.default_screen.default_depth == 32:

            # RecordingSurface won't write clear operation to surface so we
            # need to clear that surface directly.
            if getattr(self, "_xcb_surface", None) is not None:
                ctx = cairocffi.Context(self._xcb_surface)
                ctx.save()
                ctx.set_operator(cairocffi.OPERATOR_CLEAR)
                ctx.paint()
                ctx.restore()

        self.set_source_rgb(colour)
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()

    def set_source_rgb(self, colour):
        # Remove transparency from non-32 bit windows
        if utils.has_transparency(colour) and self.qtile.core.conn.default_screen.default_depth != 32:
            colour = utils.remove_transparency(colour)

        base.Drawer.set_source_rgb(self, colour)
