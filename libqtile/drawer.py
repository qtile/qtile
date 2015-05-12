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

import collections
import math
import cairocffi
import xcffib.xproto

from . import pangocffi
from . import utils


class TextLayout(object):
    def __init__(self, drawer, text, colour, font_family, font_size,
                 font_shadow, wrap=True, markup=False):
        self.drawer, self.colour = drawer, colour
        layout = drawer.ctx.create_layout()
        layout.set_alignment(pangocffi.ALIGN_CENTER)
        if not wrap:  # pango wraps by default
            layout.set_ellipsize(pangocffi.ELLIPSIZE_END)
        desc = pangocffi.FontDescription.from_string(font_family)
        desc.set_absolute_size(pangocffi.units_from_double(font_size))
        layout.set_font_description(desc)
        self.font_shadow = font_shadow
        self.layout = layout
        self.markup = markup
        self.text = text
        self._width = None

    @property
    def text(self):
        return self.layout.get_text()

    @text.setter
    def text(self, value):
        if self.markup:
            # pangocffi doesn't like None here, so we use "".
            if value is None:
                value = ''
            attrlist, value, accel_char = pangocffi.parse_markup(value)
            self.layout.set_attributes(attrlist)
        return self.layout.set_text(utils.scrub_to_utf8(value))

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

    def framed(self, border_width, border_color, pad_x, pad_y):
        return TextFrame(self, border_width, border_color, pad_x, pad_y)


class TextFrame:
    def __init__(self, layout, border_width, border_color, pad_x, pad_y):
        self.layout = layout
        self.border_width = border_width
        self.border_color = border_color
        self.drawer = self.layout.drawer

        if isinstance(pad_x, collections.Iterable):
            self.pad_left = pad_x[0]
            self.pad_right = pad_x[1]
        else:
            self.pad_left = self.pad_right = pad_x

        if isinstance(pad_y, collections.Iterable):
            self.pad_top = pad_y[0]
            self.pad_bottom = pad_y[1]
        else:
            self.pad_top = self.pad_bottom = pad_y

    def draw(self, x, y, rounded=True, fill=False):
        self.drawer.set_source_rgb(self.border_color)
        opts = [
            x, y,
            self.layout.width + self.pad_left + self.pad_right,
            self.layout.height + self.pad_top + self.pad_bottom,
            self.border_width
        ]
        if fill:
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
        self.layout.draw(
            x + self.pad_left,
            y + self.pad_top
        )

    def draw_fill(self, x, y, rounded=True):
        self.draw(x, y, rounded, fill=True)

    @property
    def height(self):
        return self.layout.height + self.pad_top + self.pad_bottom

    @property
    def width(self):
        return self.layout.width + self.pad_left + self.pad_right


class Drawer:
    """
        A helper class for drawing and text layout.

        We have a drawer object for each widget in the bar. The underlying
        surface is a pixmap with the same size as the bar itself. We draw to
        the pixmap starting at offset 0, 0, and when the time comes to display
        to the window, we copy the appropriate portion of the pixmap onto the
        window.
    """
    def __init__(self, qtile, wid, width, height):
        self.qtile = qtile
        self.wid, self.width, self.height = wid, width, height

        self.pixmap = self.qtile.conn.conn.generate_id()
        self.gc = self.qtile.conn.conn.generate_id()

        self.qtile.conn.conn.core.CreatePixmap(
            self.qtile.conn.default_screen.root_depth,
            self.pixmap,
            self.wid,
            self.width,
            self.height
        )
        self.qtile.delegate_free_at_exit(
            self.pixmap,
            self.qtile.conn.conn.core.FreePixmap)

        self.qtile.conn.conn.core.CreateGC(
            self.gc,
            self.wid,
            xcffib.xproto.GC.Foreground | xcffib.xproto.GC.Background,
            [
                self.qtile.conn.default_screen.black_pixel,
                self.qtile.conn.default_screen.white_pixel
            ]
        )
        self.qtile.delegate_free_at_exit(
            self.gc,
            self.qtile.conn.conn.core.FreeGC)

        self.surface = cairocffi.XCBSurface(
            qtile.conn.conn,
            self.pixmap,
            self.find_root_visual(),
            self.width,
            self.height,
        )
        self.ctx = self.new_ctx()
        self.clear((0, 0, 1))

    def __del__(self):
        self.qtile.do_delegated_free(self.gc)
        self.qtile.do_delegated_free(self.pixmap)

    def _rounded_rect(self, x, y, width, height, linewidth):
        aspect = 1.0
        corner_radius = height / 10.0
        radius = corner_radius / aspect
        degrees = math.pi / 180.0

        self.ctx.new_sub_path()

        delta = radius + linewidth / 2
        self.ctx.arc(x + width - delta, y + delta, radius,
                     -90 * degrees, 0 * degrees)
        self.ctx.arc(x + width - delta, y + height - delta,
                     radius, 0 * degrees, 90 * degrees)
        self.ctx.arc(x + delta, y + height - delta, radius,
                     90 * degrees, 180 * degrees)
        self.ctx.arc(x + delta, y + delta, radius,
                     180 * degrees, 270 * degrees)
        self.ctx.close_path()

    def rounded_rectangle(self, x, y, width, height, linewidth):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def rounded_fillrect(self, x, y, width, height, linewidth):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.fill()

    def rectangle(self, x, y, width, height, linewidth=2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.stroke()

    def fillrect(self, x, y, width, height, linewidth=2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()
        self.ctx.stroke()

    def draw(self, offsetx=0, offsety=0, width=None, height=None):
        """
            offsetx: the X offset to start drawing at.
            offsety: the Y offset to start drawing at.
            width: the X portion of the canvas to draw at the starting point.
            height: the Y portion of the canvas to draw at the starting point.
        """
        # ensure type consistency
        self.qtile.conn.conn.core.CopyArea(
            self.pixmap,
            self.wid,
            self.gc,
            0, 0,  # srcx, srcy
            int(offsetx), int(offsety),  # dstx, dsty
            int(self.width) if width is None else int(width),
            int(self.height) if height is None else int(height)
        )

    def find_root_visual(self):
        for i in self.qtile.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.conn.default_screen.root_visual:
                    return v

    def new_ctx(self):
        return pangocffi.CairoContext(cairocffi.Context(self.surface))

    def set_source_rgb(self, colour):
        if type(colour) == list:
            if len(colour) == 0:
                # defaults to black
                self.ctx.set_source_rgba(*utils.rgb("#000000"))
            elif len(colour) == 1:
                self.ctx.set_source_rgba(*utils.rgb(colour[0]))
            else:
                linear = cairocffi.LinearGradient(0.0, 0.0, 0.0, self.height)
                step_size = 1.0 / (len(colour) - 1)
                step = 0.0
                for c in colour:
                    rgb_col = utils.rgb(c)
                    if len(rgb_col) < 4:
                        rgb_col[3] = 1
                    linear.add_color_stop_rgba(step, *rgb_col)
                    step += step_size
                self.ctx.set_source(linear)
        else:
            self.ctx.set_source_rgba(*utils.rgb(colour))

    def clear(self, colour):
        self.set_source_rgb(colour)
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()
        self.ctx.stroke()

    def textlayout(self, text, colour, font_family, font_size, font_shadow,
                   markup=False, **kw):
        """
            Get a text layout.
        """
        return TextLayout(self, text, colour, font_family, font_size,
                          font_shadow, markup=markup, **kw)

    def max_layout_size(self, texts, font_family, font_size):
        sizelayout = self.textlayout(
            "", "ffffff", font_family, font_size, None)
        widths, heights = [], []
        for i in texts:
            sizelayout.text = i
            widths.append(sizelayout.width)
            heights.append(sizelayout.height)
        return max(widths), max(heights)

    # Old text layout functions, to be deprectated.
    def set_font(self, fontface, size, antialias=True):
        self.ctx.select_font_face(fontface)
        self.ctx.set_font_size(size)
        fo = self.ctx.get_font_options()
        fo.set_antialias(cairocffi.ANTIALIAS_SUBPIXEL)

    def text_extents(self, text):
        return self.ctx.text_extents(utils.scrub_to_utf8(text))

    def font_extents(self):
        return self.ctx.font_extents()

    def fit_fontsize(self, heightlimit):
        """
            Try to find a maximum font size that fits any strings within the
            height.
        """
        self.ctx.set_font_size(heightlimit)
        asc, desc, height, _, _ = self.font_extents()
        self.ctx.set_font_size(
            int(heightlimit * (heightlimit / float(height))))
        return self.font_extents()

    def fit_text(self, strings, heightlimit):
        """
            Try to find a maximum font size that fits all strings within the
            height.
        """
        self.ctx.set_font_size(heightlimit)
        _, _, _, maxheight, _, _ = self.ctx.text_extents("".join(strings))
        if not maxheight:
            return 0, 0
        self.ctx.set_font_size(
            int(heightlimit * (heightlimit / float(maxheight))))
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
