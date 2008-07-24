import manager, window, config
import Xlib.X

class Gap:
    def __init__(self, width):
        self.width = width
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen):
        self.qtile, self.screen = qtile, screen

    def geometry(self):
        """
            Returns (x, y, width, height)
        """
        s = self.screen
        if s.top is self:
            return s.x, s.y, s.width, self.width
        elif s.bottom is self:
            return s.x, s.dy + s.dheight, s.width, self.width
        elif s.left is self:
            return s.x, s.dy, self.width, s.dheight
        elif s.right is self:
            return s.dx + s.dwidth, s.y + s.dy, self.width, s.dheight


STRETCH = -1


class _Widget:
    fontName = "-*-fixed-bold-r-normal-*-18-*-*-*-c-*-*-*"
    fontName = "-*-freemono-bold-r-normal-*-18-*-*-*-m-*-*-*"
    @property
    def win(self):
        return self.bar.window.window

    @property
    def colormap(self):
        return self.qtile.display.screen().default_colormap

    def configure(self, qtile, bar):
        self.qtile, self.bar = qtile, bar
        self.gc = self.win.create_gc()
        self.font = qtile.display.open_font(self.fontName)


class GroupBox(_Widget):
    BOXPADDING_SIDE = 8
    BOXPADDING_TOP = 3
    PADDING = 3
    def configure(self, qtile, bar):
        _Widget.configure(self, qtile, bar)
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

    def draw(self, offset, width):
        y = self.textheight + (self.bar.width - self.textheight)/2
        x = offset + self.PADDING
        for i in self.qtile.groups:
            if self.qtile.currentGroup.name == i.name:
                self.gc.change(foreground=self.background)
                self.win.fill_rectangle(
                    self.gc, x, 0,
                    self.boxwidth, self.bar.width
                )
                self.gc.change(foreground=self.foreground)
            self.win.draw_text(
                self.gc,
                x + self.BOXPADDING_SIDE,
                y,
                i.name
            )
            x += self.boxwidth


class Bar(Gap):
    background = None
    widgets = None
    window = None
    def __init__(self, widgets, width):
        Gap.__init__(self, width)
        self.widgets = widgets

    def _configure(self, qtile, screen):
        if not self in [screen.top, screen.bottom]:
            raise config.ConfigError("Bars must be at the top or the bottom of the screen.")
        Gap._configure(self, qtile, screen)
        colormap = qtile.display.screen().default_colormap
        self.background = colormap.alloc_named_color("black").pixel
        self.window = window.Internal.create(self.qtile, self.background, *self.geometry())
        for i in self.widgets:
            i.configure(qtile, self)
        qtile.internalMap[self.window.window] = self.window
        self.window.unhide()
        self.draw()

    def draw(self):
        for i in self.widgets:
            i.draw(0, 11)



