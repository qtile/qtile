import manager, window, config
import Xlib.X

class Gap:
    def __init__(self, size):
        self.size = size
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen, event):
        self.qtile, self.screen, self.event = qtile, screen, event

    @property
    def x(self):
        s = self.screen
        if s.right is self:
            return s.dx + s.dwidth
        else:
            return s.x

    @property
    def y(self):
        s = self.screen
        if s.top is self:
            return s.y
        elif s.bottom is self:
            return s.dy + s.dheight
        elif s.left is self:
            return s.dy
        elif s.right is self:
            return s.y + s.dy

    @property
    def width(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return s.width
        else:
            return self.size

    @property
    def height(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return self.size
        else:
            return s.dheight

    def geometry(self):
        return self.x, self.y, self.width, self.height


STRETCH = -1

class Bar(Gap):
    background = None
    widgets = None
    window = None
    def __init__(self, widgets, size):
        Gap.__init__(self, size)
        self.widgets = widgets

    def _configure(self, qtile, screen, event):
        if not self in [screen.top, screen.bottom]:
            raise config.ConfigError("Bars must be at the top or the bottom of the screen.")
        Gap._configure(self, qtile, screen, event)
        colormap = qtile.display.screen().default_colormap
        self.background = colormap.alloc_named_color("black").pixel
        self.window = window.Internal.create(
                        self.qtile,
                        self.background,
                        self.x, self.y, self.width, self.height
                     )
        qtile.internalMap[self.window.window] = self.window
        self.window.unhide()

        for i in self.widgets:
            i._configure(qtile, self, event)

        offset = 0
        stretchWidget = None
        for i in self.widgets:
            i.offset = offset
            if i.width == STRETCH:
                stretchWidget = i
                break
            offset += i.width

        total = offset
        offset = self.width
        if stretchWidget:
            for i in reversed(self.widgets):
                if i.width == STRETCH:
                    break
                offset -= i.width
                total += i.width
                i.offset = offset
            stretchWidget.width = self.width - total
        self.draw()

    def draw(self):
        for i in self.widgets:
            i.draw()

    def info(self):
        return [i.info() for i in self.widgets]


class _Widget:
    """
        Each widget must set its own width attribute when the _configure method
        is called. If this is set to the special value STRETCH, the bar itself
        will set the width to the maximum remaining space, after all other
        widgets have been configured. Only ONE widget per bar can have the
        STRETCH width set.

        The offset attribute is set by the Bar after all widgets have been
        configured.
    """
    fontName = "-*-freemono-bold-r-normal-*-18-*-*-*-m-*-*-*"
    width = None
    offset = None
    @property
    def win(self):
        return self.bar.window.window

    @property
    def colormap(self):
        return self.qtile.display.screen().default_colormap

    def _configure(self, qtile, bar, event):
        self.qtile, self.bar, self.event = qtile, bar, event
        self.gc = self.win.create_gc()
        self.font = qtile.display.open_font(self.fontName)

    def info(self):
        return dict(
            name = self.__class__.__name__,
            offset = self.offset,
            width = self.width,
        )


class Spacer(_Widget):
    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.width = STRETCH

    def draw(self):
        pass


class GroupBox(_Widget):
    BOXPADDING_SIDE = 8
    BOXPADDING_TOP = 3
    PADDING = 3
    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.foreground = self.colormap.alloc_named_color("white").pixel
        self.background = self.colormap.alloc_named_color("#5866cf").pixel
        self.gc.change(foreground=self.foreground)
        self.textheight, self.textwidth = 0, 0
        for i in qtile.groups:
            data = self.font.query_text_extents(i.name)
            th = data.overall_ascent
            fw = data.overall_width
            if th > self.textheight:
                self.textheight = th
            if fw > self.textwidth:
                self.textwidth = fw
        self.boxwidth = self.BOXPADDING_SIDE*2 + self.textwidth
        self.width = self.boxwidth * len(qtile.groups) + 2 * self.PADDING
        self.event.subscribe("setgroup", self.draw)

    def draw(self):
        y = self.textheight + (self.bar.size - self.textheight)/2
        x = self.offset + self.PADDING
        for i in self.qtile.groups:
            if self.qtile.currentGroup.name == i.name:
                self.gc.change(foreground=self.background)
                self.win.fill_rectangle(
                    self.gc, x, 0,
                    self.boxwidth, self.bar.size
                )
                self.gc.change(foreground=self.foreground)
            self.win.draw_text(
                self.gc,
                x + self.BOXPADDING_SIDE,
                y,
                i.name
            )
            x += self.boxwidth

