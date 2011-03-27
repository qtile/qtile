
from base import Layout
from .. import manager
from .. import window
from .. import drawer
from .. import hook

class TreeTab(Layout):
    """Tree Tab Layout

    This layout works just like Max but displays tree of the windows at the
    left border of the screen, which allows you to overview all opened windows.
    It's designed to work with ``uzbl-browser`` but works with other windows
    too.
    """

    name = "treetab"
    defaults = manager.Defaults(
        ("bg_color", "000000", "Background color of tabs"),
        ("active_bg", "0000ff", "Background color of active tab"),
        ("active_fg", "ffffff", "Foreground color of active tab"),
        ("inactive_bg", "c0c0c0", "Background color of inactive tab"),
        ("inactive_fg", "ffffff", "Foreground color of inactive tab"),
        ("font", "Arial", "Font"),
        ("fontsize", 12, "Font pixel size."),
        ("panel_width", 150, "Width of the left panel"),
        ("sections", ['Surfing', 'News', 'Incognito'],
            "Foreground color of inactive tab"),
    )

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self._focused = None
        self._panel = None
        self._clients = []

    def clone(self, group):
        c = Layout.clone(self, group)
        c._clients = []
        c._focused = None
        c._panel = None
        return c

    def focus_first(self):
        return self._clients[0]

    def focus_last(self):
        return self._clients[-1]

    def focus_next(self, win):
        try:
            return self._clients[self._clients.index(win)+1]
        except IndexError:
            return None

    def focus_prev(self, win):
        if win == self._clients[0]:
            return None
        return self._clients[self._clients.index(win)-1]

    def focus(self, win):
        self._focused = win

    def blur(self):
        self._focused = None

    def add(self, win):
        self._clients.append(win)

    def remove(self, win):
        res = self.focus_next(win)
        if self._focused is win:
            self._focused = None
        self._clients.remove(win)
        return res

    def _create_panel(self):
        self._panel = window.Internal.create(self.group.qtile,
            self.group.screen.dx,
            self.group.screen.dy,
            self.panel_width,
            self.group.screen.dheight)
        self._drawer = drawer.Drawer(self.group.qtile, self._panel.window.wid,
            self.panel_width, self.group.screen.dheight)
        self._drawer.clear(self.bg_color)
        self._layout = self._drawer.textlayout("", "ffffff", self.font,
            self.fontsize)
        self._panel.handle_Expose = self._panel_Expose
        self._panel.handle_ButtonPress = self._panel_ButtonPress
        hook.subscribe.window_name_change(self.draw_panel)
        hook.subscribe.focus_change(self.draw_panel)

    def _panel_Expose(self):
        self.draw_panel()

    def draw_panel(self):
        if not self._panel:
            return
        self._drawer.clear(self.bg_color)
        y = 6
        for i, win in enumerate(self._clients):
            self._layout.text = win.name
            if win is self._focused:
                fg = self.active_fg
                bg = self.active_bg
            else:
                fg = self.inactive_fg
                bg = self.inactive_bg
            self._layout.colour = fg
            self._layout.width = self.panel_width
            framed = self._layout.framed(2, bg, 4, 4)
            framed.draw(6, y)
            y += self._layout.height + 4 + 4*2 + 2
        self._drawer.draw(0, self.panel_width)

    def _panel_ButtonPress(self):
        pass  # TODO

    def configure(self, c):
        if not self._panel:
            self._create_panel()
            self._panel.unhide()
            self.draw_panel()
        if self._clients and c is self._focused:
            c.place(
                self.group.screen.dx + self.panel_width,
                self.group.screen.dy,
                self.group.screen.dwidth - self.panel_width,
                self.group.screen.dheight,
                0,
                None
            )
            c.unhide()
        else:
            c.hide()

    def info(self):
        d = Layout.info(self)
        d["clients"] = [i.name for i in self._clients]
        return d

    def cmd_up(self):
        """
            Switch up in the window list
        """
        win = self.focus_next(self._focused)
        if not win:
            win = self.focus_first()
        self.group.focus(win, False)

    def cmd_down(self):
        """
            Switch down in the window list
        """
        win = self.focus_prev(self._focused)
        if not win:
            win = self.focus_last()
        self.group.focus(win, False)

