from base import Layout
from .. import utils, manager


class Floating(Layout):
    """
        Floating layout, which does nothing with windows but handles focus order
    """
    defaults = manager.Defaults(
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width.")
    )
    name = "floating"
    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.clients = []
        self.focused = None

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, win):
        idx = self.clients.index(win)
        if len(self.clients) > idx+1:
            return self.clients[idx+1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_prev(self, win):
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx-1]
            
    def focus(self, c):
        self.focused = c
    
    def blur(self):
        self.focused = None
    
    def configure(self, c):
        if c is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        c.place(c.x,
               c.y,
               c.width,
               c.height,
               self.border_width,
               bc)
        c.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, c):
        self.clients.append(c)

    def remove(self, c):
        res = self.focus_next(c)
        self.clients.remove(c)
        return res

    def info(self):
        d = Layout.info(self)
        d["clients"] = [i.name for i in self.clients]
        return d
