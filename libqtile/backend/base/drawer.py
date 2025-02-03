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

import collections
import math
import typing

import cairocffi

from libqtile import pangocffi, utils

if typing.TYPE_CHECKING:
    from libqtile.backend.base import Internal
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType


class Drawer:
    """A helper class for drawing to Internal windows.

    We stage drawing operations locally in memory using a cairo RecordingSurface before
    finally drawing all operations to a backend-specific target.
    """

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        self.qtile = qtile
        self._win = win
        self._width = width
        self._height = height

        self.surface: cairocffi.RecordingSurface
        self.last_surface: cairocffi.RecordingSurface
        self.ctx: cairocffi.Context
        self._reset_surface()

        self._has_mirrors = False

        self._enabled = True

    def finalize(self):
        """Destructor/Clean up resources"""
        if hasattr(self, "surface"):
            self.surface.finish()
            delattr(self, "surface")
        if hasattr(self, "last_surface"):
            self.last_surface.finish()
            delattr(self, "last_surface")
        self.ctx = None

    @property
    def has_mirrors(self):
        return self._has_mirrors

    @has_mirrors.setter
    def has_mirrors(self, value):
        if value and not self._has_mirrors:
            self._create_last_surface()

        self._has_mirrors = value

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int):
        self._width = width

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, height: int):
        self._height = height

    def _reset_surface(self):
        """This creates a fresh surface and cairo context."""
        if hasattr(self, "surface"):
            self.surface.finish()

        self.surface = cairocffi.RecordingSurface(
            cairocffi.CONTENT_COLOR_ALPHA,
            None,
        )
        self.ctx = self.new_ctx()

    def _create_last_surface(self):
        """Creates a separate RecordingSurface for mirrors to access."""
        if hasattr(self, "last_surface"):
            self.last_surface.finish()
        self.last_surface = cairocffi.RecordingSurface(cairocffi.CONTENT_COLOR_ALPHA, None)

    def paint_to(self, drawer: Drawer) -> None:
        drawer.ctx.set_source_surface(self.last_surface)
        drawer.ctx.paint()

    def _rounded_rect(self, x, y, width, height, linewidth):
        aspect = 1.0
        corner_radius = height / 10.0
        radius = corner_radius / aspect
        degrees = math.pi / 180.0

        self.ctx.new_sub_path()

        delta = radius + linewidth / 2
        self.ctx.arc(x + width - delta, y + delta, radius, -90 * degrees, 0 * degrees)
        self.ctx.arc(x + width - delta, y + height - delta, radius, 0 * degrees, 90 * degrees)
        self.ctx.arc(x + delta, y + height - delta, radius, 90 * degrees, 180 * degrees)
        self.ctx.arc(x + delta, y + delta, radius, 180 * degrees, 270 * degrees)
        self.ctx.close_path()

    def rounded_rectangle(self, x: int, y: int, width: int, height: int, linewidth: int):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def rounded_fillrect(self, x: int, y: int, width: int, height: int, linewidth: int):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.fill()

    def rectangle(self, x: int, y: int, width: int, height: int, linewidth: int = 2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.stroke()

    def fillrect(self, x: int, y: int, width: int, height: int, linewidth: int = 2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()
        self.ctx.stroke()

    def enable(self):
        """Enable drawing of surface to Internal window."""
        self._enabled = True

    def disable(self):
        """Disable drawing of surface to Internal window."""
        self._enabled = False

    def draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
        src_x: int = 0,
        src_y: int = 0,
    ):
        """
        A wrapper for the draw operation.

        This draws our cached operations to the Internal window.

        If Drawer has been disabled then the RecordingSurface will
        be cleared if no mirrors are waiting to copy its contents.

        Parameters
        ==========

        offsetx :
            the X offset to start drawing at.
        offsety :
            the Y offset to start drawing at.
        width :
            the X portion of the canvas to draw at the starting point.
        height :
            the Y portion of the canvas to draw at the starting point.
        src_x  :
            the X position of the origin in the source surface
        src_y  :
            the Y position of the origin in the source surface
        """
        if self._enabled:
            self._draw(
                offsetx=offsetx,
                offsety=offsety,
                width=width,
                height=height,
                src_x=src_x,
                src_y=src_y,
            )
            if self.has_mirrors:
                self._create_last_surface()
                ctx = cairocffi.Context(self.last_surface)
                ctx.set_source_surface(self.surface)
                ctx.paint()

        self._reset_surface()

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
        src_x: int = 0,
        src_y: int = 0,
    ):
        """
        This draws our cached operations to the Internal window.

        Parameters
        ==========

        offsetx :
            the X offset to start drawing at.
        offsety :
            the Y offset to start drawing at.
        width :
            the X portion of the canvas to draw at the starting point.
        height :
            the Y portion of the canvas to draw at the starting point.
        src_x  :
            the X position of the origin in the source surface
        src_y  :
            the Y position of the origin in the source surface
        """

    def new_ctx(self):
        return pangocffi.patch_cairo_context(cairocffi.Context(self.surface))

    def set_source_rgb(self, colour: ColorsType, ctx: cairocffi.Context | None = None):
        # If an alternate context is not provided then we draw to the
        # drawer's default context
        if ctx is None:
            ctx = self.ctx
        if isinstance(colour, list):
            if len(colour) == 0:
                # defaults to black
                ctx.set_source_rgba(0.0, 0.0, 0.0, 1.0)
            elif len(colour) == 1:
                ctx.set_source_rgba(*utils.rgb(colour[0]))
            else:
                linear = cairocffi.LinearGradient(0.0, 0.0, 0.0, self.height)
                step_size = 1.0 / (len(colour) - 1)
                step = 0.0
                for c in colour:
                    linear.add_color_stop_rgba(step, *utils.rgb(c))
                    step += step_size
                ctx.set_source(linear)
        else:
            ctx.set_source_rgba(*utils.rgb(colour))

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

        self.ctx.save()
        self.ctx.set_operator(cairocffi.OPERATOR_CLEAR)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()
        self.ctx.restore()

    def clear(self, colour):
        """Clears background of the Drawer and fills with specified colour."""
        if self.ctx is None:
            self._reset_surface()
        self.ctx.save()

        # Erase the background
        self.clear_rect()

        # Fill drawer with new colour
        self.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.set_source_rgb(colour)
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()

        self.ctx.restore()

    def textlayout(self, text, colour, font_family, font_size, font_shadow, markup=False, **kw):
        """Get a text layout"""
        textlayout = TextLayout(
            self, text, colour, font_family, font_size, font_shadow, markup=markup, **kw
        )
        return textlayout

    def max_layout_size(self, texts, font_family, font_size, markup=False):
        sizelayout = self.textlayout("", "ffffff", font_family, font_size, None, markup=markup)
        widths, heights = [], []
        for i in texts:
            sizelayout.text = i
            widths.append(sizelayout.width)
            heights.append(sizelayout.height)
        return max(widths), max(heights)

    def text_extents(self, text):
        return self.ctx.text_extents(utils.scrub_to_utf8(text))

    def font_extents(self):
        return self.ctx.font_extents()

    def fit_fontsize(self, heightlimit):
        """Try to find a maximum font size that fits any strings within the height"""
        self.ctx.set_font_size(heightlimit)
        asc, desc, height, _, _ = self.font_extents()
        self.ctx.set_font_size(int(heightlimit * heightlimit / height))
        return self.font_extents()

    def fit_text(self, strings, heightlimit):
        """Try to find a maximum font size that fits all strings within the height"""
        self.ctx.set_font_size(heightlimit)
        _, _, _, maxheight, _, _ = self.ctx.text_extents("".join(strings))
        if not maxheight:
            return 0, 0
        self.ctx.set_font_size(int(heightlimit * heightlimit / maxheight))
        maxwidth, maxheight = 0, 0
        for i in strings:
            _, _, x, y, _, _ = self.ctx.text_extents(i)
            maxwidth = max(maxwidth, x)
            maxheight = max(maxheight, y)
        return maxwidth, maxheight

    def draw_vbar(self, color, x, y1, y2, linewidth=1):
        self.set_source_rgb(color)
        self.ctx.move_to(x, y1)
        self.ctx.line_to(x, y2)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def draw_hbar(self, color, x1, x2, y, linewidth=1):
        self.set_source_rgb(color)
        self.ctx.move_to(x1, y)
        self.ctx.line_to(x2, y)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()


class TextLayout:
    def __init__(
        self, drawer, text, colour, font_family, font_size, font_shadow, wrap=True, markup=False
    ):
        self.drawer, self.colour = drawer, colour
        layout = drawer.ctx.create_layout()
        layout.set_alignment(pangocffi.ALIGN_CENTER)
        if not wrap:  # pango wraps by default
            layout.set_ellipsize(pangocffi.ELLIPSIZE_END)
        desc = pangocffi.FontDescription.from_string(font_family)
        desc.set_absolute_size(pangocffi.units_from_double(float(font_size)))
        layout.set_font_description(desc)
        self.font_shadow = font_shadow
        self.layout = layout
        self.markup = markup
        self.text = text
        self._width = None

    def finalize(self):
        self.layout.finalize()

    def finalized(self):
        self.layout.finalized()

    @property
    def text(self):
        return self.layout.get_text()

    @text.setter
    def text(self, value):
        if self.markup:
            # pangocffi doesn't like None here, so we use "".
            if value is None:
                value = ""
            attrlist, value, accel_char = pangocffi.parse_markup(value)
            self.layout.set_attributes(attrlist)
        self.layout.set_text(utils.scrub_to_utf8(value))

    @property
    def width(self):
        if self._width is not None:
            return self._width
        else:
            return self.layout.get_pixel_size()[0]

    @width.setter
    def width(self, value):
        self._width = value
        self.layout.set_width(pangocffi.units_from_double(value))

    @width.deleter
    def width(self):
        self._width = None
        self.layout.set_width(-1)

    @property
    def height(self):
        return self.layout.get_pixel_size()[1]

    def fontdescription(self):
        return self.layout.get_font_description()

    @property
    def font_family(self):
        d = self.fontdescription()
        return d.get_family()

    @font_family.setter
    def font_family(self, font):
        d = self.fontdescription()
        d.set_family(font)
        self.layout.set_font_description(d)

    @property
    def font_size(self):
        d = self.fontdescription()
        return d.get_size()

    @font_size.setter
    def font_size(self, size):
        d = self.fontdescription()
        d.set_size(size)
        d.set_absolute_size(pangocffi.units_from_double(size))
        self.layout.set_font_description(d)

    def draw(self, x, y):
        if self.font_shadow is not None:
            self.drawer.set_source_rgb(self.font_shadow)
            self.drawer.ctx.move_to(x + 1, y + 1)
            self.drawer.ctx.show_layout(self.layout)

        self.drawer.set_source_rgb(self.colour)
        self.drawer.ctx.move_to(x, y)
        self.drawer.ctx.show_layout(self.layout)

    def framed(self, border_width, border_color, pad_x, pad_y, highlight_color=None):
        return TextFrame(
            self, border_width, border_color, pad_x, pad_y, highlight_color=highlight_color
        )


class TextFrame:
    def __init__(self, layout, border_width, border_color, pad_x, pad_y, highlight_color=None):
        self.layout = layout
        self.border_width = border_width
        self.border_color = border_color
        self.drawer = self.layout.drawer
        self.highlight_color = highlight_color

        if isinstance(pad_x, collections.abc.Iterable):
            self.pad_left = pad_x[0]
            self.pad_right = pad_x[1]
        else:
            self.pad_left = self.pad_right = pad_x

        if isinstance(pad_y, collections.abc.Iterable):
            self.pad_top = pad_y[0]
            self.pad_bottom = pad_y[1]
        else:
            self.pad_top = self.pad_bottom = pad_y

    def draw(self, x, y, rounded=True, fill=False, line=False, highlight=False):
        self.drawer.set_source_rgb(self.border_color)
        opts = [
            x,
            y,
            self.layout.width + self.pad_left + self.pad_right,
            self.layout.height + self.pad_top + self.pad_bottom,
            self.border_width,
        ]
        if line:
            if highlight:
                self.drawer.set_source_rgb(self.highlight_color)
                self.drawer.fillrect(*opts)
                self.drawer.set_source_rgb(self.border_color)

            # change to only fill in bottom line
            opts[1] = self.height - self.border_width  # y
            opts[3] = self.border_width  # height

            self.drawer.fillrect(*opts)
        elif fill:
            if rounded:
                self.drawer.rounded_fillrect(*opts)
            else:
                self.drawer.fillrect(*opts)
        else:
            if rounded:
                self.drawer.rounded_rectangle(*opts)
            else:
                self.drawer.rectangle(*opts)
        self.drawer.ctx.stroke()
        self.layout.draw(x + self.pad_left, y + self.pad_top)

    def draw_fill(self, x, y, rounded=True):
        self.draw(x, y, rounded=rounded, fill=True)

    def draw_line(self, x, y, highlighted):
        self.draw(x, y, line=True, highlight=highlighted)

    @property
    def height(self):
        return self.layout.height + self.pad_top + self.pad_bottom

    @property
    def width(self):
        return self.layout.width + self.pad_left + self.pad_right
