import math
from .. import command, utils, bar, manager
import xcb.xproto
import cairo, pangocairo, pango


def scrub_to_utf8(text):
    if not text:
        return ""
    elif isinstance(text, unicode):
        return text
    else:
        try:
            return text.decode("utf-8")
        except UnicodeDecodeError:
            # We don't know the provenance of this string - so we scrub it to ASCII.
            return "".join(i for i in text if 31 < ord(i) <  127)
        

LEFT = object()
CENTER = object()
class _Drawer:
    """
        A helper class for drawing and text layout.

        We have a drawer object for each widget in the bar. The underlying
        surface is a pixmap with the same size as the bar itself. We draw to
        the pixmap starting at offset 0, 0, and when the time comes to display
        to the window, we copy the appropriate portion of the pixmap onto the
        window.
    """
    def __init__(self, qtile, widget):
        self.qtile, self.widget = qtile, widget
        self.pixmap = self.qtile.conn.conn.generate_id()
        self.gc = self.qtile.conn.conn.generate_id()

        self.qtile.conn.conn.core.CreatePixmap(
            self.qtile.conn.default_screen.root_depth,
            self.pixmap,
            widget.win.wid,
            widget.bar.width,
            widget.bar.height
        )
        self.qtile.conn.conn.core.CreateGC(
            self.gc,
            widget.win.wid,
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
                            widget.bar.width,
                            widget.bar.height
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

    def set_font(self, fontface, size, antialias=True):
        self.ctx.select_font_face(fontface)
        self.ctx.set_font_size(size)
        fo = self.ctx.get_font_options()
        fo.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

    def text_extents(self, text):
        return self.ctx.text_extents(scrub_to_utf8(text))

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

    def draw(self):
        self.qtile.conn.conn.core.CopyArea(
            self.pixmap,
            self.widget.win.wid,
            self.gc,
            0, 0, # srcx, srcy
            self.widget.offset, 0, # dstx, dsty
            self.widget.width, self.widget.bar.height
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
        self.ctx.rectangle(0, 0, self.widget.bar.width, self.widget.bar.height)
        self.ctx.fill()
        self.ctx.stroke()

    def textlayout(self, text, colour, font, fontsize):
        """
            Get a text layout.
        """
        self.ctx.set_source_rgb(*utils.rgb(colour))
        layout = self.ctx.create_layout()
        layout.set_text(scrub_to_utf8(text))
        layout.set_alignment(pango.ALIGN_LEFT)

        desc = pango.FontDescription()
        desc.set_family(font)
        desc.set_absolute_size(fontsize * pango.SCALE)
        layout.set_font_description(desc)

        return layout



class _Widget(command.CommandObject):
    """
        If width is set to the special value bar.STRETCH, the bar itself
        will set the width to the maximum remaining space, after all other
        widgets have been configured. Only ONE widget per bar can have the
        bar.STRETCH width set.

        The offset attribute is set by the Bar after all widgets have been
        configured.
    """
    offset = None
    name = None
    defaults = manager.Defaults()
    def __init__(self, width, **config):
        """
            width: bar.STRETCH, bar.CALCULATED, or a specified width.
        """
        command.CommandObject.__init__(self)
        self.defaults.load(self, config)
        if width in (bar.CALCULATED, bar.STRETCH):
            self.width_type = width
            self.width = 0
        else:
            self.width_type = bar.STATIC
            self.width = width

    @property
    def width(self):
        if self.width_type == bar.CALCULATED:
            return self.calculate_width()
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def win(self):
        return self.bar.window.window

    def _configure(self, qtile, bar):
        self.qtile, self.bar = qtile, bar
        self.drawer = _Drawer(qtile, self)

    def resize(self):
        """
            Should be called whenever widget changes size.
        """
        self.bar.resize()
        self.bar.draw()
    
    def clear(self):
        self.drawer.rectangle(
            self.offset, 0, self.width, self.bar.size,
            self.bar.background
        )

    def info(self):
        return dict(
            name = self.__class__.__name__,
            offset = self.offset,
            width = self.width,
        )

    def click(self, x, y):
        pass

    def get(self, q, name):
        """
            Utility function for quick retrieval of a widget by name.
        """
        w = q.widgetMap.get(name)
        if not w:
            raise command.CommandError("No such widget: %s"%name)
        return w

    def _items(self, name):
        if name == "bar":
            return True, None

    def _select(self, name, sel):
        if name == "bar":
            return self.bar

    def cmd_info(self):
        """
            Info for this object.
        """
        return dict(name=self.name)

    def draw(self):
        """
            Method that draws the widget. You may call this explicitly to
            redraw the widget, but only if the width of the widget hasn't
            changed. If it has, you must call bar.draw instead.
        """
        raise NotImplementedError

    def calculate_width(self):
        """
            Must be implemented if the widget can take CALCULATED for width.
        """
        raise NotImplementedError



class TextLayout(object):
    def __init__(self, ctx, text, colour, font_family, font_size):
        self.ctx, self.colour = ctx, colour
        layout = ctx.create_layout()
        layout.set_alignment(pango.ALIGN_LEFT)
        desc = pango.FontDescription()
        desc.set_family(font_family)
        desc.set_absolute_size(font_size * pango.SCALE)
        layout.set_font_description(desc)
        layout.set_ellipsize(pango.ELLIPSIZE_END)
        self.layout = layout
        self.text = text

    @property
    def text(self):
        return self.layout.get_text()

    @text.setter
    def text(self, value):
        return self.layout.set_text(scrub_to_utf8(value))

    @property
    def width(self):
        return self.layout.get_pixel_size()[0]

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
        self.ctx.move_to(x, y)
        self.ctx.set_source_rgb(*utils.rgb(self.colour))
        self.ctx.show_layout(self.layout)



UNSPECIFIED = bar.Obj("UNSPECIFIED")


class _TextBox(_Widget):
    """
        Base class for widgets that are just boxes containing text.
    
        If you derive from this class, you must add the following defaults:

            font
            fontsize
            padding
            background
            foreground
    """
    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        self.layout = None
        _Widget.__init__(self, width, **config)
        self.text = text

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        if self.layout:
            self.layout.text = value

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value
        if self.layout:
            self.layout.font = value

    @property
    def fontsize(self):
        if self._fontsize is None:
            return self.bar.height-self.bar.height/5
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value
        if self.layout:
            self.layout.font_size = value

    @property
    def actual_padding(self):
        if self.padding is None:
            return self.fontsize/2
        else:
            return self.padding

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        self.layout = TextLayout(
                    self.drawer.ctx,
                    self.text,
                    self.foreground,
                    self.font,
                    self.fontsize
                 )

    def calculate_width(self):
        if self.text:
            return min(self.layout.width, self.bar.width) + self.actual_padding * 2
        else:
            return 0

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self.layout.draw(
            self.actual_padding or 0,
            int(self.bar.height/2.0 - self.layout.height/2.0)
        )
        self.drawer.draw()

    def cmd_set_font(self, font=UNSPECIFIED, fontsize=UNSPECIFIED):
        """
            Change the font used by this widget. If font is None, the current
            font is used.
        """
        if font is not UNSPECIFIED:
            self.font = font
        if fontsize is not UNSPECIFIED:
            self.fontsize = fontsize
        self.bar.draw()
