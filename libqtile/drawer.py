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

import collections

from libqtile import pangocffi, utils


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
