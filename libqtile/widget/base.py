import sys, math
from .. import command, utils, bar
import xcb.xproto
import cairo


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
    _fallbackFont = "-*-fixed-bold-r-normal-*-15-*-*-*-c-*-*-*"
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
        return self.ctx.text_extents(text)

    def fit_fontsize(self, heightlimit):
        """
            Try to find a maximum font size that fits any strings within the
            height.
        """
        self.ctx.set_font_size(heightlimit)
        asc, desc, height, _, _  = self.ctx.font_extents()
        self.ctx.set_font_size(int(heightlimit*(heightlimit/float(height))))
        return self.ctx.font_extents()

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
        return cairo.Context(self.surface)

    def clear(self, colour):
        self.ctx.set_source_rgb(*utils.rgb(colour))
        self.ctx.rectangle(0, 0, self.widget.bar.width, self.widget.bar.height)
        self.ctx.fill()
        self.ctx.stroke()
        
    def textbox(self, text):
        """
            Draw text using the current font.
        """
        self.ctx.set_source_rgb(*utils.rgb("ffffff"))
        self.ctx.show_text(text)


class _Widget(command.CommandObject):
    """
        Each widget must set its own width attribute when the _configure method
        is called. If this is set to the special value bar.STRETCH, the bar itself
        will set the width to the maximum remaining space, after all other
        widgets have been configured. Only ONE widget per bar can have the
        bar.STRETCH width set.

        The offset attribute is set by the Bar after all widgets have been
        configured.
    """
    width = None
    offset = None
    name = None

    @property
    def win(self):
        return self.bar.window.window

    def _configure(self, qtile, bar, theme):
        self.qtile, self.bar, self.theme = qtile, bar, theme
        self.drawer = _Drawer(qtile, self)

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


class _TextBox(_Widget):
    PADDING = 5
    FONTSIZE = 20
    def __init__(self, text=" ", width=bar.STRETCH):
        self.width = width
        self.text = text

    def draw(self):
        self.drawer.clear("000000")
        asc, desc, height, xadv, _ = self.drawer.fit_fontsize(self.bar.height*0.8)
        self.drawer.ctx.move_to(xadv/2, self.bar.height*0.1 + height-desc)
        self.drawer.textbox(self.text)
        self.drawer.draw()




