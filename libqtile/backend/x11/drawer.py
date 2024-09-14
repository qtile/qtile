# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 oitel
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2012, 2014 roger
# Copyright (c) 2012 nullzion
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Nathan Hoad
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2020, 2021 Robert Andrew Ditthardt
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

import contextlib
from typing import TYPE_CHECKING

import cairocffi
import xcffib.xproto

from libqtile import utils
from libqtile.backend.base import drawer

if TYPE_CHECKING:
    from libqtile.backend.base import Internal
    from libqtile.core.manager import Qtile


class Drawer(drawer.Drawer):
    """A helper class for drawing to Internal windows.

    The underlying surface here is an XCBSurface backed by a pixmap. We draw to the
    pixmap starting at offset 0, 0, and when the time comes to display to the window (on
    draw()), we copy the appropriate portion of the pixmap onto the window. In the event
    that our drawing area is resized, we invalidate the underlying surface and pixmap
    and recreate them when we need them again with the new geometry.
    """

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        drawer.Drawer.__init__(self, qtile, win, width, height)
        self._xcb_surface = None
        self._gc = None
        self._depth, self._visual = qtile.core.conn.default_screen._get_depth_and_visual(
            win._depth
        )
        # Create an XCBSurface and pixmap
        self._check_xcb()

    def finalize(self):
        self._free_xcb_surface()
        self._free_pixmap()
        self._free_gc()
        drawer.Drawer.finalize(self)

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
        # Paint RecordingSurface operations to the XCBSurface
        ctx = cairocffi.Context(self._xcb_surface)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
        src_x: int = 0,
        src_y: int = 0,
    ):
        # If this is our first draw, create the gc
        if self._gc is None:
            self._gc = self._create_gc()

        # Recreate an XCBSurface
        self._check_xcb()

        # paint stored operations(if any) to XCBSurface
        self._paint()

        # Finally, copy XCBSurface's underlying pixmap to the window.
        self.qtile.core.conn.conn.core.CopyArea(
            self._pixmap,
            self._win.wid,
            self._gc,
            src_x,
            src_y,  # srcx, srcy
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

    def set_source_rgb(self, colour, ctx=None):
        # Remove transparency from non-32 bit windows
        if utils.has_transparency(colour) and self._depth != 32:
            colour = utils.remove_transparency(colour)

        drawer.Drawer.set_source_rgb(self, colour, ctx)

    def clear_rect(self, x=0, y=0, width=0, height=0):
        """
        Erases the background area specified by parameters. By default,
        the whole Drawer is cleared.

        The ability to clear a smaller area may be useful when you want to
        erase a smaller area of the drawer (e.g. drawing widget decorations).
        """
        if width <= 0:
            width = self.width
        if height <= 0:
            height = self.height

        self._check_xcb()

        # Using OPERATOR_CLEAR in a RecordingSurface does not clear the
        # XCBSurface so we clear the XCBSurface directly.
        with cairocffi.Context(self._xcb_surface) as ctx:
            ctx.set_operator(cairocffi.OPERATOR_CLEAR)
            ctx.rectangle(x, y, width, height)
            ctx.fill()
