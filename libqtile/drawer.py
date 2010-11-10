import utils, math
import pangocairo, cairo, pango
import xcb.xproto


class TextLayout(object):
    def __init__(self, drawer, text, colour, font_family, font_size):
        self.drawer, self.colour = drawer, colour
        layout = drawer.ctx.create_layout()
        layout.set_alignment(pango.ALIGN_CENTER)
        desc = pango.FontDescription()
        desc.set_family(font_family)
        desc.set_absolute_size(font_size * pango.SCALE)
        layout.set_font_description(desc)
        self.layout = layout
        self.text = text
        self._width = None

    @property
    def text(self):
        return self.layout.get_text()

    @text.setter
    def text(self, value):
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
        self.layout.set_width(value * pango.SCALE)

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
        d.set_absolute_size(size * pango.SCALE)
        self.layout.set_font_description(d)

    def draw(self, x, y):
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.colour))
        self.drawer.ctx.move_to(x, y)
        self.drawer.ctx.show_layout(self.layout)

    def framed(self, border_width, border_color, pad_x, pad_y):
        return TextFrame(self, border_width, border_color, pad_x, pad_y)


class TextFrame:
    def __init__(self, layout, border_width, border_color, pad_x, pad_y):
        self.layout, self.pad_x = layout, pad_x
        self.pad_y, self.border_width = pad_y, border_width
        self.border_color = border_color
        self.drawer = self.layout.drawer

    def draw(self, x, y):
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.border_color))
        self.drawer.rounded_rectangle(
            x, y,
            self.layout.width + self.pad_x * 2,
            self.layout.height + self.pad_y * 2,
            self.border_width
        )
        self.drawer.ctx.stroke()
        self.layout.draw(
            x + self.pad_x,
            y + self.pad_y
        )


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
            xcb.xproto.GC.Foreground | xcb.xproto.GC.Background,
            [
                self.qtile.conn.default_screen.black_pixel,
                self.qtile.conn.default_screen.white_pixel
            ]
        )
        self.surface = cairo.XCBSurface(
                            qtile.conn.conn,
                            self.pixmap,
                            self.find_root_visual(),
                            self.width,
                            self.height,
                        )
        self.ctx = self.new_ctx()
        self.clear((0, 0, 1))

    def rounded_rectangle(self, x, y, width, height, linewidth):
        aspect = 1.0
        corner_radius = height / 10.0
        radius = corner_radius / aspect
        degrees = math.pi/180.0

        self.ctx.new_sub_path()

        delta = radius + linewidth/2
        self.ctx.arc(x + width - delta, y + delta, radius, -90 * degrees, 0 * degrees)
        self.ctx.arc(x + width - delta, y + height - delta, radius, 0 * degrees, 90 * degrees)
        self.ctx.arc(x + delta, y + height - delta, radius, 90 * degrees, 180 * degrees)
        self.ctx.arc(x + delta, y + delta, radius, 180 * degrees, 270 * degrees)
        self.ctx.close_path()

        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def rectangle(self, x, y, width, height, linewidth):
        self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.stroke()

    def fillrect(self, x, y, w, h, colour):
        self.ctx.set_source_rgb(*utils.rgb(colour))
        self.ctx.rectangle(x, y, w, h)
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
            0, 0, # srcx, srcy
            offset, 0, # dstx, dsty
            width, self.height
        )

    def find_root_visual(self):
        for i in self.qtile.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.conn.default_screen.root_visual:
                    return v

    def new_ctx(self):
        return pangocairo.CairoContext(cairo.Context(self.surface))

    def clear(self, colour):
        self.ctx.set_source_rgb(*utils.rgb(colour))
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()
        self.ctx.stroke()

    def textlayout(self, text, colour, font_family, font_size):
        """
            Get a text layout.

            NB: the return value of this function should be saved, and reused
            to avoid a huge memory leak in the pygtk bindings. Once this has
            been repaired, we can make the semantics easier.

            https://bugzilla.gnome.org/show_bug.cgi?id=625287
        """
        return TextLayout(self, text, colour, font_family, font_size)

    _sizelayout = None
    def max_layout_size(self, texts, font_family, font_size):
        # FIXME: This is incredibly clumsy, to avoid a memory leak in pygtk. See         
        # comment on textlayout() for details.
        if not self._sizelayout:
            self._sizelayout = self.textlayout("", "ffffff", font_family, font_size)
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
        fo.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

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
        asc, desc, height, _, _  = self.font_extents()
        self.ctx.set_font_size(int(heightlimit*(heightlimit/float(height))))
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
        self.ctx.set_font_size(int(heightlimit*(heightlimit/float(maxheight))))
        maxwidth, maxheight = 0, 0
        for i in strings:
            _, _, x, y, _, _ = self.ctx.text_extents(i)
            maxwidth = max(maxwidth, x)
            maxheight = max(maxheight, y)
        return maxwidth, maxheight
