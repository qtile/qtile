from .base import SingleWindow
from .. import utils


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
        self.focused = None

    def _get_window(self):
        return self.focused

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_last(self):
        if self.clients:
            return self.clients[len(self.clients) - 1]

    def focus_next(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_previous(self, client):
        if not self.clients:
            return
        idx = self.clients.index(client)
        if idx > 0:
            return self.clients[idx - 1]

    def clone(self, group):
        c = SingleWindow.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        self.clients.insert(0, client)
        self.focus(client)

    def remove(self, client):
        if client not in self.clients:
            return
        if self.focused == client:
            self.cmd_previous()
        self.clients.remove(client)
        return self.focused

    def configure(self, client, screen):
        left, right = screen.hsplit(screen.width - self.columnwidth)
        if client is self.focused:
            client.place(
                left.x,
                left.y,
                left.width,
                left.height,
                0,
                None
            )
        else:
            h = int(right.width * left.height / left.width)
            client_index = self.clients.index(client)
            focused_index = self.clients.index(self.focused)
            offset = client_index - focused_index - 1
            if offset < 0:
                offset += len(self.clients)
            if h * (len(self.clients) - 1) < right.height:
                client.place(
                    right.x,
                    right.y + h * offset,
                    right.width,
                    h,
                    0,
                    None
                )
            else:
                hh = int((right.height - h) / (len(self.clients) - 1))
                client.place(
                    right.x,
                    right.y + hh * offset,
                    right.width,
                    h,
                    0,
                    None
                )
        client.unhide()

    def info(self):
        d = SingleWindow.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def focus(self, win):
        if self.focused and self.property_name:
            self.focused.window.set_property(
                self.property_name,
                self.property_small,
                "STRING",
                format=8
            )
        SingleWindow.focus(self, win)
        if self.property_name:
            self.focused = win
            win.window.set_property(
                self.property_name,
                self.property_big,
                "STRING",
                format=8
            )

    def cmd_next(self):
        client = self.focus_next(self.focused) or self.focus_first()
        self.group.focus(client, False)

    cmd_down = cmd_next

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or self.focus_last()
        self.group.focus(client, False)

    cmd_up = cmd_previous
