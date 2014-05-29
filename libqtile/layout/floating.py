from base import Layout
from .. import window
from ..config import Match
from .. import hook

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

        self._clients    = []
        self._focused    = []
        self._save       = []
        self._transients = dict()

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
            win.x     = new_x
            win.y     = new_y
            win.group = new_screen.group

    def focus_first(self):
        if self._clients and \
        self._clients[0] not in \
        self._focused:
            self._focused.append(self._clients[0])
            return self._clients[0]

    def focus_last(self):
        if self._clients and \
        self._clients[-1] not in \
        self._focused:
            self._focused.append(self._clients[-1])
            return self._clients[-1]

    def focus_next(self, win):
        if win not in self._clients:
            return
        idx = self._clients.index(win)
        if len(self._clients) > idx + 1:
            if self._clients[idx + 1] not in self._focused:
                self._focused.append(self._clients[idx + 1])
            return self._clients[idx + 1]

    def focus_previous(self, win):
        if win not in self._clients:
            return
        idx = self._clients.index(win)
        if idx > 0:
            if self._clients[idx -1] not in self._focused:
                self._focused.append(self._clients[idx -1])
            return self._clients[idx - 1]

    def focus(self, client):
        if client not in self._focused:
            self._focused.append(client)

    def focus_transients(self, client):
        if client.window.wid in self._transients:
            self._focused = self._transients[client.window.wid]

    def save_focused(self):
        self._save = self._focused

    def restore_focused(self):
        self._focused = self._save
        self._save = []

    def blur(self, client = None):
        if(client):
            if client in self._focused:
                self._focused.remove(client)
        else:
            self._focused = []

    def configure(self, client, screen):
        client_in_list = False
        if client in self._focused:
            client_in_list = True
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
            client_in_list,
        )
        client.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c._clients    = []
        c._focused    = []
        c._save       = []
        c._transients = dict()
        return c

    def add(self, client):
        if client not in self._clients:
            self._clients.append(client)
        if client not in self._focused:
            self._focused.append(client)

        wm_transient_for = client.window.get_wm_transient_for()
        if wm_transient_for:
            if not self._transients.get(wm_transient_for, None):
                self._transients[wm_transient_for] = [client]
            else:
                self._transients[wm_transient_for].append(client)

    def remove(self, client):
        if client not in self._clients:
            return
        if client in self._focused:
            self._focused.remove(client)

        remove = []
        for k,v in self._transients.items():
            if client in v:
                v.remove(client)
            if not v:
                remove.append(k)
        for k in remove:
            self._transients.pop(k)

        nextclient = self.focus_next(client)
        self._clients.remove(client)
        return nextclient

    @property
    def clients(self):
        """Clients which are being managed by this layout"""
        return self._clients

    @property
    def focused(self):
        """Clients which are currently focused"""
        return self._focused

    @property
    def transients(self):
        return self._transients

    @focused.setter
    def focused(self, client):
        """Set focus on clients"""
        self.add(client)

    def info(self):
        d = Layout.info(self)
        d["clients"] = [x.name for x in self._clients]
        d["focused"] = [x.name for x in self._focused]
        return d

    def cmd_next(self):
        client = self.focus_next(self._focused) or \
                 self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self._focused) or \
                 self.focus_last()
        self.group.focus(client, False)
