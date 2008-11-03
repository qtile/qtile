from .. import command, utils, bar

LEFT = object()
CENTER = object()
class _Drawer:
    """
        A helper class for drawing and text layout.
    """
    _fallbackFont = "-*-fixed-bold-r-normal-*-15-*-*-*-c-*-*-*"
    def __init__(self, qtile, window):
        self.qtile, self.window = qtile, window
        self.win = window.window
        self.gc = self.win.create_gc()
        self.colormap = qtile.display.screen().default_colormap
        self.background, self.foreground = None, None
        
    @utils.LRUCache(100)
    def color(self, color):
        return self.colormap.alloc_named_color(color).pixel

    def setFont(self, font):
        f = self.qtile.display.open_font(font)
        if not f:
            self.qtile.log.add("Could not open font %s, falling back."%font)
            f = self.qtile.display.open_font(self._fallbackFont)
        self.font = f
        self.gc.change(font=f)

    @utils.LRUCache(100)
    def text_extents(self, font, i):
        return font.query_text_extents(i)

    def textsize(self, font, *text):
        """
            Return a textheight, textwidth tuple, for a box large enough to
            enclose any of the passed strings.
        """
        textheight, textwidth = 0, 0
        for i in text:
            data = self.text_extents(font, i)
            if  data.font_ascent > textheight:
                textheight = data.font_ascent
            if data.overall_width > textwidth:
                textwidth = data.overall_width
        return textheight, textwidth

    def change(self, **kwargs):
        newargs = kwargs.copy()
        newargs.pop("background", None)
        newargs.pop("foreground", None)
        if kwargs.has_key("background") and self.background != kwargs["background"]:
            self.background = kwargs["background"]
            newargs["background"] = self.color(kwargs["background"])
        if kwargs.has_key("foreground") and self.background != kwargs["foreground"]:
            self.background = kwargs["foreground"]
            newargs["foreground"] = self.color(kwargs["foreground"])
        if newargs:
            self.gc.change(**newargs)

    def textbox(self, text, x, y, width, height, padding = 0,
                alignment=LEFT, background=None, **attrs):
        """
            Draw text in the specified box using the current font. Text is
            centered vertically, and left-aligned. 
            
            :background Fill box with the specified color first.
            :padding  Padding to the left of the text.
        """
        text = text or " "
        if background:
            self.rectangle(x, y, width, height, background)
            attrs["background"] = background
        if attrs:
            self.change(**attrs)
        textheight, textwidth = self.textsize(self.font, text)
        y = y + textheight + (height - textheight)/2
        if alignment == LEFT:
            x = x + padding
        else:
            x = x + (width - textwidth)/2
        self.win.draw_text(self.gc, x, y, text)

    def rectangle(self, x, y, width, height, fillColor=None, borderColor=None, borderWidth=1):
        if fillColor:
            self.change(foreground=fillColor)
            self.win.fill_rectangle(self.gc, x, 0, width, height)
        if borderColor:
            self.change(
                foreground=borderColor,
                line_width=borderWidth
            )
            self.win.rectangle(self.gc, x, 0, width, height)


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
    font = "-*-luxi mono-*-r-*-*-12-*-*-*-*-*-*-*"
    width = None
    offset = None
    name = None

    @property
    def win(self):
        return self.bar.window.window

    @property
    def colormap(self):
        return self.qtile.display.screen().default_colormap

    def _configure(self, qtile, bar, event):
        self.qtile, self.bar, self.event = qtile, bar, event
        self._drawer = _Drawer(qtile, self.bar.window)
        self._drawer.setFont(self.font)

    def clear(self):
        self._drawer.rectangle(
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
    def __init__(self, text=" ", width=bar.STRETCH, foreground="white",
                 background=bar._HIGHLIGHT, font=None):
        self.width, self.foreground, self.background = width, foreground, background
        self.text = text
        if font:
            self.font = font

    def draw(self):
        self._drawer.textbox(
            self.text,
            self.offset, 0, self.width, self.bar.size,
            padding = self.PADDING,
            foreground=self.foreground,
            background=self.background,
        )

