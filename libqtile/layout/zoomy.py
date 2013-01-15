from base import SingleWindow
from .. import utils, manager


class Zoomy(SingleWindow):
    """
        A layout with single active windows, and few other previews at the
        right
    """
    defaults = [
        ("columnwidth", 150, "Width of the right column"),
        ("property_name", "ZOOM", "Property to set on zoomed window"),
        ("property_small", "0.1", "Property value to set on zoomed window"),
        ("property_big", "1.0", "Property value to set on normal window"),
    ]

    def __init__(self, **config):
        SingleWindow.__init__(self, **config)
        self.add_defaults(Zoomy.defaults)
        self.clients = []
        self.lastfocus = None

    def _get_window(self):
        if self.clients:
            return self.clients[0]

    def up(self):
        if self.clients:
            utils.shuffleUp(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], False)

    def down(self):
        if self.clients:
            utils.shuffleDown(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], False)

    def clone(self, group):
        c = SingleWindow.clone(self, group)
        c.clients = []
        return c

    def add(self, c):
        self.clients.insert(0, c)

    def remove(self, c):
        self.clients.remove(c)
        if self.clients:
            return self.clients[0]

    def configure(self, c, screen):
        left, right = screen.hsplit(screen.width - self.columnwidth)
        if self.clients and c is self.clients[0]:
            c.place(
                left.x,
                left.y,
                left.width,
                left.height,
                0,
                None
            )
        else:
            h = int(right.width * left.height / left.width)
            if h * (len(self.clients) - 1) < right.height:
                c.place(
                    right.x,
                    right.y + h * (self.clients.index(c) - 1),
                    right.width,
                    h,
                    0,
                    None
                    )
            else:
                hh = int((right.height - h) / (len(self.clients) - 1))
                c.place(
                    right.x,
                    right.y + hh * (self.clients.index(c) - 1),
                    right.width,
                    h,
                    0,
                    None
                    )
        c.unhide()

    def info(self):
        d = SingleWindow.info(self)
        d["clients"] = [i.name for i in self.clients]
        return d

    def focus(self, win):
        old = self.lastfocus
        if old and self.property_name:
            old.window.set_property(self.property_name,
                self.property_small, "STRING", format=8)
        SingleWindow.focus(self, win)
        if self.property_name:
            win = self.clients[0]
            win.window.set_property(self.property_name,
                self.property_big, "STRING", format=8)
        self.lastfocus = win

    def cmd_down(self):
        """
            Switch down in the window list.
        """
        self.down()

    def cmd_up(self):
        """
            Switch up in the window list.
        """
        self.up()
