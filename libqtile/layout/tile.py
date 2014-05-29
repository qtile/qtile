from base import Layout
from ..config import Match
from .. import utils


class Tile(Layout):
    defaults = [
        ("name", "tile", "Name of this layout."),
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("margin", 0, "Margin of the layout."),
        ("ratio", 0.618, "Ratio of the layout."),
        ("ratio_increment", 0.05, "Ratio increment value."),
        ("expand", True, "Whether to expand."),
        ("add_on_top", True, "Add on top."),
        ("shift_windows", False, "Shift windows."),
        ("num_masterwindows", 1, "Number of master windows."),
        ("match", None, "Match object."
         "Matching windows will become a master window."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Tile.defaults)
        self.clients = []
        self.focused = None

    @property
    def master_windows(self):
        return self.clients[:self.num_masterwindows]

    @property
    def slave_windows(self):
        return self.clients[self.num_masterwindows:]

    def up(self):
        if self.shift_windows:
            self.shift_up()
        else:
            self.shuffle(utils.shuffleUp)

    def down(self):
        if self.shift_windows:
            self.shift_down()
        else:
            self.shuffle(utils.shuffleDown)

    def shift_up(self):
        if self.clients:
            currentindex = self.clients.index(self.focused)
            nextindex = self.get_next_index(currentindex)
            self.shift(currentindex, nextindex)

    def shift_down(self):
        if self.clients:
            currentindex = self.clients.index(self.focused)
            previndex = self.get_previous_index(currentindex)
            self.shift(currentindex, previndex)

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_previous(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        if idx > 0:
            return self.clients[idx - 1]

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll(True)

    def resetMaster(self, match=None):
        if not match and self.match:
            match = self.match
        else:
            return
        if self.clients:
            masters = [c for c in self.clients if match.compare(c)]
            self.clients = masters + [
                c for c in self.clients if c not in masters
            ]

    def shift(self, idx1, idx2):
        if self.clients:
            self.clients[idx1], self.clients[idx2] = \
                self.clients[idx2], self.clients[idx1]
            self.group.layoutAll(True)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, client):
        self.focused = client

    def blur(self):
        self.focused = None

    def add(self, client):
        index = 0
        if not self.add_on_top and self.clients and self.focused:
            index = self.clients.index(self.focused)
        self.clients.insert(index, client)
        self.resetMaster()

    def remove(self, client):
        if client not in self.clients:
            return

        if self.focused is client:
            self.focused = None

        self.clients.remove(client)
        if self.clients and client is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, client, screen):
        screenWidth = screen.width
        screenHeight = screen.height
        x = 0
        y = 0
        w = 0
        h = 0
        borderWidth = self.border_width
        margin = self.margin
        if self.clients and client in self.clients:
            pos = self.clients.index(client)
            if client in self.master_windows:
                w = int(screenWidth * self.ratio) \
                    if len(self.slave_windows) or not self.expand \
                    else screenWidth
                h = screenHeight / self.num_masterwindows
                x = screen.x
                y = screen.y + pos * h
            else:
                w = screenWidth - int(screenWidth * self.ratio)
                h = screenHeight / (len(self.slave_windows))
                x = screen.x + int(screenWidth * self.ratio)
                y = screen.y + self.clients[self.num_masterwindows:].index(client) * h
            if client is self.focused:
                bc = self.group.qtile.colorPixel(self.border_focus)
            else:
                bc = self.group.qtile.colorPixel(self.border_normal)
            client.place(
                x + margin,
                y + margin,
                w - margin * 2 - borderWidth * 2,
                h - margin * 2 - borderWidth * 2,
                borderWidth,
                bc,
            )
            client.unhide()
        else:
            client.hide()

    def info(self):
        return dict(
            name=self.name,
            clients=[c.name for c in self.clients],
            master=[c.name for c in self.master_windows],
            slave=[c.name for c in self.slave_windows],
        )

    def cmd_down(self):
        self.down()

    def cmd_up(self):
        self.up()

    def cmd_next(self):
        client = self.focus_next(self.focused) or \
                 self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or \
                 self.focus_last()
        self.group.focus(client, False)

    def cmd_decrease_ratio(self):
        self.ratio -= self.ratio_increment
        self.group.layoutAll()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layoutAll()

    def cmd_decrease_nmaster(self):
        self.num_masterwindows -= 1
        if self.num_masterwindows <= 0:
            self.num_masterwindows = 1
        self.group.layoutAll()

    def cmd_increase_nmaster(self):
        self.num_masterwindows += 1
        self.group.layoutAll()
