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
        self._clients = []
        self._focused = []

    def to_screen(self, new_screen):
        """
        Adjust offsets of clients within current screen
        """
        for i, win in enumerate(self._clients):
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
        if self._clients:
            if not self._clients[0] in self._focused:
                self._focused.append(self._clients[0])
            return self._clients[0]

    def focus_next(self, win):
        if win not in self._clients:
            return
        idx = self._clients.index(win)
        if len(self._clients) > idx + 1:
            if not self._clients[idx +1] in self._focused:
                self._focused.append(self._clients[idx + 1])
            return self._clients[idx + 1]

    def focus_last(self):
        if self._clients:
            if not self._clients[-1] in self._focused:
                self._focused.append(self._clients[-1])
            return self._clients[-1]

    def focus_previous(self, win):
        if win not in self._clients:
            return
        idx = self._clients.index(win)
        if idx > 0:
            if not self._clients[idx -1] in self._focused:
                self._focused.append(self._clients[idx -1])
            return self._clients[idx - 1]

    def focus(self, client):
        if not client in self._focused:
            self._focused.append(client)

    def focus_toggle(self, client):
        if client not in self._focused:
            self.focus(client)
        else:
            self.blur(client)

    def blur(self, group = None, client = None):
        if(group):
            for focused in self._focused:
                if getattr(focused, 'group', None) == group:
                    self._focused.remove(focused)
        elif(client):
            if client in self._focused:
                self._focused.remove(client)
        else:
            self._focused = []

    def configure(self, client, screen):
        clientinlist = False
        if client in self._focused:
            clientinlist = True
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
            clientinlist,
        )
        client.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c._clients = []
        c._focused = []
        return c

    def add(self, client):
        self._clients.append(client)
        if not client in self._focused:
            self._focused.append(client)

    def remove(self, client):
        if client not in self._clients:
            return
        nextclient = self.focus_next(client)
        self._clients.remove(client)
        if client in self._focused:
            self._focused.remove(client)
        return self._focused

    def info(self):
        d = Layout.info(self)
        d["clients"] = [x.name for x in self._clients]
        d["focused"] = [x.name for x in self._focused]
        return d

    @property
    def clients(self):
        return self._clients

    @property
    def focused(self):
        return self._focused

    @focused.setter
    def focused(self, client):
        if not client in self._focused:
            self._focused.append(client)

    def cmd_next(self):
        client = self.focus_next(self._focused) or \
                 self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self._focused) or \
                 self.focus_last()
        self.group.focus(client, False)
