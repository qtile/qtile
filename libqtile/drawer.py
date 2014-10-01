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
        desc = pangocffi.FontDescription()
        desc.set_family(font_family)
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
        self.qtile.conn.conn.core.CreateGC(
            self.gc,
            self.wid,
            xcffib.xproto.GC.Foreground | xcffib.xproto.GC.Background,
            [
                self.qtile.conn.default_screen.black_pixel,
                self.qtile.conn.default_screen.white_pixel
            ]
        )
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
        self.qtile.conn.conn.core.FreeGC(self.gc)
        self.qtile.conn.conn.core.FreePixmap(self.pixmap)

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

    def draw(self, offset, width):
        """
            offset: the X offset to start drawing at.
            width: the portion of the canvas to draw at the starting point.
        """
        self.qtile.conn.conn.core.CopyArea(
            self.pixmap,
            self.wid,
            self.gc,
            0, 0,  # srcx, srcy
            offset, 0,  # dstx, dsty
            width, self.height
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

            NB: the return value of this function should be saved, and reused
            to avoid a huge memory leak in the pygtk bindings. Once this has
            been repaired, we can make the semantics easier.

            https://bugzilla.gnome.org/show_bug.cgi?id=625287
        """
        return TextLayout(self, text, colour, font_family, font_size,
                          font_shadow, markup=markup, **kw)

    _sizelayout = None

    def max_layout_size(self, texts, font_family, font_size):
        # FIXME: This is incredibly clumsy, to avoid a memory leak in pygtk.
        # See comment on textlayout() for details.
        if not self._sizelayout:
            self._sizelayout = self.textlayout(
                "", "ffffff", font_family, font_size, None)
        widths, heights = [], []
        self._sizelayout.font_family = font_family
        self._sizelayout.font_size = font_size
        for i in texts:
            self._sizelayout.text = i
            widths.append(self._sizelayout.width)
            heights.append(self._sizelayout.height)
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
