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
        self._pseudo_surface = None
        self.pseudo_pixmap = None
        self._root_surface = None
        self._root_pixmap = None

    def finalize(self):
        self._free_surfaces()
        self._free_pixmaps()
        self._free_gc()
        base.Drawer.finalize(self)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > self._width:
            self._free_surfaces()
            self._free_pixmaps()
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        if height > self._height:
            self._free_surfaces()
            self._free_pixmaps()
        self._height = height

    @property
    def pixmap(self):
        if self._pixmap is None:
            # draw here since the only use case of this function is in the
            # systray widget which expects a filled pixmap.
            self.draw()
        return self._pixmap

    @property
    def base_surface(self):
        """
        For reasons with transparency and widget mirrors, we don't draw
        backgrounds to the recording surface. Instead these are drawns straight
        to the underlying XCBSurface.

        Where we use pseudotransparency, we still need to draw the background
        separately (so it's not copied to mirrors) but this should not be
        an XCBSurface as this results in errors with transparency. We therefore
        use a separate recording surface.
        """
        if self.pseudotransparent:
            surface = self._pseudo_surface
        else:
            surface = self._xcb_surface

        return surface

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

    def _create_xcb_surface(self, pixmap=None):
        pixmap = self._pixmap if pixmap is None else pixmap
        surface = cairocffi.XCBSurface(
            self.qtile.core.conn.conn,
            pixmap,
            self._visual,
            self.width,
            self.height,
        )
        return surface

    def _free_surfaces(self):
        for surface in [
            self._xcb_surface,
            self.surface,
            self._pseudo_surface,
            self._root_surface,
        ]:
            if surface is not None:
                surface.finish()
                surface = None

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

    def _free_pixmaps(self):
        for pixmap in [self._pixmap, self.pseudo_pixmap]:
            if pixmap is not None:
                with contextlib.suppress(xcffib.ConnectionException):
                    self.qtile.core.conn.conn.core.FreePixmap(pixmap)
                pixmap = None

    def _check_base_surface(self):
        # If the Drawer has been resized/invalidated we need to recreate these
        if self.pseudotransparent:
            if self._pseudo_surface is None:
                self.pseudo_pixmap = self._create_pixmap()
                self._root_surface = self._create_xcb_surface(self.pseudo_pixmap)
                self._create_pseudo_surface()
        else:
            if self._xcb_surface is None:
                self._pixmap = self._create_pixmap()
                self._xcb_surface = self._create_xcb_surface()

    def _paint(self):
        # Only attempt to run RecordingSurface's operations if ie actually need to
        if self.needs_update:
            ctx = cairocffi.Context(self.base_surface)
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

        if self.pseudotransparent and self._root_pixmap is None:
            self._root_pixmap = self._get_root_pixmap()
            if self._root_pixmap is None:
                logger.warning(
                    "Cannot find pixmap for root window. Disabling pseudotransparency."
                )
                self.pseudotransparent = False

        self.current_rect = (offsetx, offsety, width, height)

        width = self.width if not width else width
        height = self.height if not height else height

        # If this is our first draw, create the gc
        if self._gc is None:
            self._gc = self._create_gc()

        # Check if we need to re-create XCBSurface
        # This may not be needed now that we call in `clear`
        self._check_base_surface()

        # paint stored operations(if any) to XCBSurface
        self._paint()

        if self.pseudotransparent:
            self.pseudo_draw(offsetx, offsety, width, height)

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
                height,
            )

    def _find_root_visual(self):
        for i in self.qtile.core.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.core.conn.default_screen.root_visual:
                    return v

    def clear(self, colour):
        # Check if we need to re-create base surface
        self._check_base_surface()

        mode = cairocffi.OPERATOR_OVER if self.pseudotransparent else cairocffi.OPERATOR_SOURCE

        ctx = cairocffi.Context(self.base_surface)
        ctx.save()
        ctx.set_operator(mode)
        self.set_source_rgb(colour, ctx=ctx)
        ctx.paint()
        ctx.restore()

    def set_source_rgb(self, colour, ctx=None):
        # Remove transparency from non-32 bit and non-pseudotransparent windows
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

    def _create_pseudo_surface(self):
        self._pseudo_surface = cairocffi.RecordingSurface(cairocffi.CONTENT_COLOR_ALPHA, None)
        self.pseudo_ctx = cairocffi.Context(self._pseudo_surface)

    def _get_root_pixmap(self):
        root_win = self.qtile.core.conn.default_screen.root

        try:
            root_pixmap = root_win.get_property("_XROOTPMAP_ID", xcffib.xproto.Atom.PIXMAP, int)
        except xcffib.ConnectionException:
            root_pixmap = None

        if not root_pixmap:
            root_pixmap = root_win.get_property(
                "ESETROOT_PMAP_ID", xcffib.xproto.Atom.PIXMAP, int
            )
        if root_pixmap:
            return root_pixmap[0]

    def pseudo_draw(self, x, y, width, height):
        widget_pos = (
            self.widget.bar.screen.x + self.widget.bar.window.x + self.widget.offsetx,
            self.widget.bar.screen.y + self.widget.bar.window.y + self.widget.offsety,
        )

        self.qtile.core.conn.conn.core.CopyArea(
            self._root_pixmap,
            self.pseudo_pixmap,
            self._gc,
            *widget_pos,
            0,
            0,
            width,
            height,
        )

        ctx = cairocffi.Context(self._root_surface)
        ctx.set_source_surface(self._pseudo_surface)
        ctx.paint()

        self.qtile.core.conn.conn.core.CopyArea(
            self.pseudo_pixmap,
            self._win.wid,
            self._gc,
            0,
            0,
            x,
            y,  # dstx, dsty
            width,
            height,
        )
        
        self._create_pseudo_surface()
