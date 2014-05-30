from base import Layout
from .. import window
from ..config import Match

class Floating(Layout):
    """
    Floating layout, which does nothing with windows but handles focus order
    """
    DEFAULT_FLOAT_WM_TYPES = Match(
    wm_type=[
        'utility',
        'notification',
        'toolbar',
        'splash',
        'dialog',]
    )

    defaults = [
        ("name", "floating", "Name of this layout."),
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("max_border_width", 0, "Border width for maximize."),
        ("fullscreen_border_width", 0, "Border width for fullscreen."),
        ("match",DEFAULT_FLOAT_WM_TYPES,
         "Match object. Windows matching it will float."
         "Concatenate Floating.DEFAULT_FLOAT_WM_TYPES with your own"
         "Match object to add windows to match. Or insert into a MatchList."),
    ]

    def __init__(self, **config):
        """
        If you have certain applications which should float,
        you can concatenate a Match object containing matches
        for those applications with Floating.DEFAULT_FLOAT_WM_TYPES.
        """
        Layout.__init__(self, **config)
        self.add_defaults(Floating.defaults)
        self.clients = []
        self._focused = None

    def to_screen(self, new_screen):
        """
        Adjust offsets of clients within current screen
        """
        for i, win in enumerate(self.clients):
            if win.maximized:
                win.enablemaximize()
                continue
            elif win.fullscreen:
                win.enablemaximize(state=window.FULLSCREEN)
                continue

            offset_x = win._float_info['x']
            offset_y = win._float_info['y']

            if offset_x > 0:
                new_x = new_screen.x + offset_x
            else:
                new_x = new_screen.x + i * 10
            if offset_y > 0:
                new_y = new_screen.y + offset_y
            else:
                new_y = new_screen.y + i * 10

            right_edge = new_screen.x + new_screen.width
            bottom_edge = new_screen.y + new_screen.height
            while new_x > right_edge:
                new_x = (new_x - new_screen.x) / 2
            while new_y > bottom_edge:
                new_y = (new_y - new_screen.y) / 2
            win.x = new_x
            win.y = new_y
            win.group = new_screen.group

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, win):
        if win not in self.clients:
            return
        idx = self.clients.index(win)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_previous(self, win):
        if win not in self.clients:
            return
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx - 1]

    def focus(self, client):
        self._focused = client

    def blur(self):
        self._focused = None

    def configure(self, client, screen):
        if client is self._focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        if client.maximized:
            bw = self.max_border_width
        elif client.fullscreen:
            bw = self.fullscreen_border_width
        else:
            bw = self.border_width
        client.place(
            client.x,
            client.y,
            client.width,
            client.height,
            bw,
            bc,
            client is self._focused
        )
        client.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        self.clients.append(client)
        self._focused = client

    def remove(self, client):
        if client not in self.clients:
            return
        self._focused = self.focus_next(client)
        self.clients.remove(client)
        return self._focused

    def info(self):
        d = Layout.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def cmd_next(self):
        client = self.focus_next(self._focused) or \
                 self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self._focused) or \
                 self.focus_last()
        self.group.focus(client, False)
