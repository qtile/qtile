from .. import command, utils, bar, manager, drawer

import gobject


LEFT = object()
CENTER = object()


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
        self.drawer = drawer.Drawer(
                            qtile,
                            self.win.wid,
                            self.bar.width,
                            self.bar.height
                      )

    def resize(self):
        """
            Should be called whenever widget changes size.
        """
        self.bar.resize()
        self.bar.draw()

    def clear(self):
        self.drawer.set_source_rgb(self.bar.background)
        self.drawer.fillrect(self.offset, 0, self.width, self.bar.size)

    def info(self):
        return dict(
            name = self.__class__.__name__,
            offset = self.offset,
            width = self.width,
        )

    def click(self, x, y, button):
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

    def timeout_add(self, seconds, method, *args):
        """
            This method calls either ``gobject.timeout_add`` or
            ``gobject.timeout_add_seconds`` with same arguments. Latter is
            better for battery usage, but works only with integer timeouts
        """
        if int(seconds) == seconds:
            return gobject.timeout_add_seconds(int(seconds), method, *args)
        else:
            return gobject.timeout_add(int(seconds*1000), method, *args)



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
        self.layout = self.drawer.textlayout(
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
        self.drawer.draw(self.offset, self.width)

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
