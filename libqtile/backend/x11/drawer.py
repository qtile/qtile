from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import cairocffi
import xcffib.xproto

from libqtile import utils
from libqtile.backend import base
from libqtile.log_utils import logger

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
        self._depth, self._visual = qtile.core.conn.default_screen._get_depth_and_visual(
            win._depth
        )
        self.pseudotransparent = False
        self.root_pixmap = None

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
            with contextlib.suppress(xcffib.ConnectionException):
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
            with contextlib.suppress(xcffib.ConnectionException):
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
            if self.pseudotransparent:
                surface = self.pseudo_surface
            else:
                surface = self._xcb_surface
            ctx = cairocffi.Context(surface)
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

        if self.pseudotransparent and self.root_pixmap is None:
            self.root_pixmap = self._get_root_pixmap()
            if self.root_pixmap is None:
                logger.warning("Cannot find pixmap for root window. Disabling pseudotransparency.")
                self.pseudotransparent = False

        self.current_rect = (offsetx, offsety, width, height)

        width = self.width if not width else width
        height = self.height if not height else height

        # If this is our first draw, create the gc
        if self._gc is None:
            self._gc = self._create_gc()

        # Check if we need to re-create XCBSurface
        # This may not be needed now that we call in `clear`
        self._check_xcb()

        # paint stored operations(if any) to XCBSurface
        self._paint()

        if self.pseudotransparent:
            self.draw_with_root(offsetx, offsety, width, height)

        else:

            # Finally, copy XCBSurface's underlying pixmap to the window.
            self.qtile.core.conn.conn.core.CopyArea(
                self._pixmap,
                self._win.wid,
                self._gc,
                0,
                0,  # srcx, srcy
                offsetx,
                offsety,  # dstx, dsty
                width,
                height
            )

    def _find_root_visual(self):
        for i in self.qtile.core.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.core.conn.default_screen.root_visual:
                    return v

    def clear(self, colour):

        # Check if we need to re-create XCBSurface
        self._check_xcb()

        if self.pseudotransparent:
            surface = self.pseudo_surface
            mode = cairocffi.OPERATOR_OVER
        else:
            surface = self._xcb_surface
            mode = cairocffi.OPERATOR_SOURCE

        ctx = cairocffi.Context(surface)
        ctx.save()
        # ctx.set_operator(mode)
        self.set_source_rgb(colour, ctx=ctx)
        ctx.paint()
        ctx.restore()

    def set_source_rgb(self, colour, ctx=None):
        # Remove transparency from non-32 bit windows
        if utils.has_transparency(colour) and (self._depth != 32 and not self.pseudotransparent):
            colour = utils.remove_transparency(colour)

        base.Drawer.set_source_rgb(self, colour, ctx)

    def set_pseudo_transparency(self, widget):
        """
        Tell drawer to use pseudo transparency for widgets.

        We need reference to the widget so we can calculate position on screen and use
        this to copy correct part of root pixmap.
        """
        self.pseudotransparent = True
        self.widget = widget
        self._create_pseudo_surface()

    def _create_pseudo_surface(self):
        self.pseudo_surface = cairocffi.RecordingSurface(
            cairocffi.CONTENT_COLOR_ALPHA,
            None
        )

    def _get_root_pixmap(self):
        root_win = self.qtile.core.conn.default_screen.root

        try:
            root_pixmap = root_win.get_property(
                "_XROOTPMAP_ID", xcffib.xproto.Atom.PIXMAP, int
            )
        except xcffib.ConnectionException:
            root_pixmap = None

        if not root_pixmap:
            root_pixmap = root_win.get_property(
                "ESETROOT_PMAP_ID", xcffib.xproto.Atom.PIXMAP, int
            )
        if root_pixmap:
            return root_pixmap[0]

    def draw_with_root(self, x, y, w, h):

        widget_pos = (
            self.widget.bar.screen.x + self.widget.bar.window.x + self.widget.offsetx,
            self.widget.bar.screen.y + self.widget.bar.window.y + self.widget.offsety,
        )

        pix_root = self.qtile.core.conn.conn.generate_id()

        self.qtile.core.conn.conn.core.CreatePixmap(
            self._depth,
            pix_root,
            self._win.wid,
            w,
            h
        )
        self.qtile.core.conn.conn.core.CopyArea(
            self.root_pixmap,
            pix_root,
            self._gc,
            *widget_pos,
            0,
            0,
            w,
            h,
        )

        surf_root = cairocffi.XCBSurface(self.qtile.core.conn.conn, pix_root, self._visual, w, h)
        ctx = cairocffi.Context(surf_root)

        ctx.set_source_surface(self.pseudo_surface)
        ctx.paint()

        self.qtile.core.conn.conn.core.CopyArea(
            pix_root,
            self._win.wid,
            self._gc,
            0,
            0,
            x,
            y,  # dstx, dsty
            w,
            h,
        )
        self.pseudopixmap = pix_root
        # self.qtile.core.conn.conn.flush()
        self._create_pseudo_surface()
