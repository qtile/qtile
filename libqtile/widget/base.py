import sys
from .. import command, utils, bar
import cairo

LEFT = object()
CENTER = object()
class _Drawer:
    """
        A helper class for drawing and text layout.
    """
    _fallbackFont = "-*-fixed-bold-r-normal-*-15-*-*-*-c-*-*-*"
    def __init__(self, qtile, window):
        self.qtile, self.window = qtile, window
        self.surface = cairo.XCBSurface(
                            qtile.conn.conn,
                            window.window.wid,
                            self.find_root_visual(),
                            window.width,
                            window.height
                        )
        self.set_background((0, 0, 1))

    def find_root_visual(self):
        for i in self.qtile.conn.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.qtile.conn.default_screen.root_visual:
                    return v

    def ctx(self):
        return cairo.Context(self.surface)

    def set_background(self, colour):
        c = self.ctx()
        c.set_source_rgb(*colour)
        c.rectangle(0, 0, self.window.width, self.window.height)
        c.fill()
        c.stroke()
        
    def textbox(self, text, x, y, width, height, padding = 0,
                alignment=LEFT, background=None, **attrs):
        """
            Draw text in the specified box using the current font. Text is
            centered vertically, and left-aligned. 
            
            :background Fill box with the specified color first.
            :padding  Padding to the left of the text.
        """
        pass

    def rectangle(self, x, y, width, height, fillColor=None, borderColor=None, borderWidth=1):
        pass


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

    def _configure(self, qtile, bar, theme):
        self.qtile, self.bar, self.theme = qtile, bar, theme
        self._drawer = _Drawer(qtile, self.bar.window)

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
    def __init__(self, text=" ", width=bar.STRETCH):
        self.width = width
        self.text = text

    def _configure(self, qtile, bar, theme):
        _Widget._configure(self, qtile, bar, theme)
        if theme.font:
            self.font = theme.font

    def draw(self):
        self._drawer.textbox(
            self.text,
            self.offset, 0, self.width, self.bar.size,
            padding = self.PADDING,
            foreground=self.theme.fg_normal,
            background=self.theme.bg_normal,
        )

