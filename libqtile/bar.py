import sys
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
    background = "black"
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
        c = colormap.alloc_named_color(self.background).pixel
        self.window = window.Internal.create(
                        self.qtile,
                        c,
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



class _Graph:
    """
        A helper class for drawing and text layout.
    """
    _fallbackFont = "-*-fixed-bold-r-normal-*-15-*-*-*-c-*-*-*"
    def __init__(self, qtile, window):
        self.qtile, self.window = qtile, window
        self.win = window.window
        self.gc = self.win.create_gc()
        self.colormap = qtile.display.screen().default_colormap
        self.colors = {}
        
    def color(self, color):
        if self.colors.has_key(color):
            return self.colors[color]
        else:
            c = self.colormap.alloc_named_color(color).pixel
            self.colors[color] = c
            return c

    def setFont(self, font):
        f = self.qtile.display.open_font(font)
        if not f:
            self.qtile.log.add("Could not open font %s, falling back."%font)
            f = self.qtile.display.open_font(self._fallbackFont)
        self.font = f
        _, self.font_ascent = self.textsize("A")
        self.gc.change(font=f)

    def textsize(self, *text):
        """
            Return a textheight, textwidth tuple, for a box large enough to
            enclose any of the passed strings.
        """
        textheight, textwidth = 0, 0
        for i in text:
            data = self.font.query_text_extents(i)
            if  data.font_ascent > textheight:
                textheight = data.font_ascent
            if data.overall_width > textwidth:
                textwidth = data.overall_width
        return textheight, textwidth

    def change(self, **kwargs):
        if kwargs.has_key("background"):
            kwargs["background"] = self.color(kwargs["background"])
        if kwargs.has_key("foreground"):
            kwargs["foreground"] = self.color(kwargs["foreground"])
        self.gc.change(**kwargs)

    def textbox(self, text, x, y, width, height, padding = 0, background=None, **attrs):
        """
            Draw text in the specified box using the current font. Text is
            centered vertically, and left-aligned. 
            
            :background Fill box with the specified color first.
            :padding  Padding to the left of the text.
        """
        if background:
            self.rectangle(x, y, width, height, background)
        if attrs:
            self.change(**attrs)
        y = y + self.font_ascent + (height - self.font_ascent)/2
        self.win.draw_text(self.gc, x + padding, y, text)

    def rectangle(self, x, y, width, height, color):
        self.change(foreground=color)
        self.win.fill_rectangle(self.gc, x, 0, width, height)


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
    font = "-*-luxi mono-*-r-*-*-12-*-*-*-*-*-*-*"
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
        self.graph = _Graph(qtile, self.bar.window)
        self.graph.setFont(self.font)

    def clear(self):
        self.graph.rectangle(
            self.offset, 0, self.width, self.bar.size,
            self.bar.background
        )

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
    PADDING = 3
    def __init__(self, foreground="white", background="#5866cf", font=None):
        self.foreground, self.background = foreground, background
        if font:
            self.font = font

    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.textheight, self.textwidth = self.graph.textsize(*[i.name for i in qtile.groups])
        self.boxwidth = self.BOXPADDING_SIDE*2 + self.textwidth
        self.width = self.boxwidth * len(qtile.groups) + 2 * self.PADDING
        self.event.subscribe("setgroup", self.draw)

    def draw(self):
        self.clear()
        x = self.offset + self.PADDING
        for i in self.qtile.groups:
            background = None
            if self.bar.screen.group.name == i.name:
                background = self.background
            self.graph.textbox(
                i.name,
                x, 0, self.boxwidth, self.bar.size,
                padding = self.BOXPADDING_SIDE,
                foreground = self.foreground,
                background = background
            )
            x += self.boxwidth


class WindowName(_Widget):
    PADDING = 5
    def __init__(self, width=STRETCH, foreground="white", background="#5866cf", font=None):
        self.width, self.foreground, self.background = width, foreground, background
        if font:
            self.font = font

    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.event.subscribe("window_name_change", self.draw)
        self.event.subscribe("focus_change", self.draw)

    def draw(self):
        w = self.bar.screen.group.currentWindow
        if w:
            self.graph.textbox(
                w.name,
                self.offset, 0, self.width, self.bar.size,
                padding = self.PADDING,
                foreground=self.foreground,
                background=self.background,
            )
