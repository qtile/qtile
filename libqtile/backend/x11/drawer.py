from __future__ import annotations

from typing import TYPE_CHECKING

import cairocffi
import xcffib.xproto

from libqtile import utils
from libqtile.backend import base

if TYPE_CHECKING:
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
        self._depth, self._visual = qtile.core.conn.default_screen._get_depth_and_visual(win._depth)  # type: ignore

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
            self._visual,
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
            self._depth,
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

    def _check_xcb(self):
        # If the Drawer has been resized/invalidated we need to recreate these
        if self._xcb_surface is None:
            self._pixmap = self._create_pixmap()
            self._xcb_surface = self._create_xcb_surface()

    def _paint(self):
        # Only attempt to run RecordingSurface's operations if ie actually need to
        if self.needs_update:
            # Paint RecordingSurface operations to the XCBSurface
            ctx = cairocffi.Context(self._xcb_surface)
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.paint()

            self.previous_rect = self.current_rect

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
    ):

        self.current_rect = (offsetx, offsety, width, height)

        # If this is our first draw, create the gc
        if self._gc is None:
            self._gc = self._create_gc()

        # Check if we need to re-create XCBSurface
        # This may not be needed now that we call in `clear`
        self._check_xcb()

        # paint stored operations(if any) to XCBSurface
        self._paint()

        # Finally, copy XCBSurface's underlying pixmap to the window.
        self.qtile.core.conn.conn.core.CopyArea(  # type: ignore
            self._pixmap,
            self._win.wid,
            self._gc,
            0,
            0,  # srcx, srcy
            offsetx,
            offsety,  # dstx, dsty
            self.width if width is None else width,
            self.height if height is None else height,
        )

    def _find_root_visual(self):
        for i in self.qtile.core.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.core.conn.default_screen.root_visual:
                    return v

    def clear(self, colour):

        # Check if we need to re-create XCBSurface
        self._check_xcb()

        # Draw background straigt to XCB surface
        ctx = cairocffi.Context(self._xcb_surface)
        ctx.save()
        ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.set_source_rgb(colour, ctx=ctx)
        ctx.paint()
        ctx.restore()

    def set_source_rgb(self, colour, ctx=None):
        # Remove transparency from non-32 bit windows
        if utils.has_transparency(colour) and self._depth != 32:
            colour = utils.remove_transparency(colour)

        base.Drawer.set_source_rgb(self, colour, ctx)
