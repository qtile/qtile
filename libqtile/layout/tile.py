from base import Layout
from .. import utils, manager


class Tile(Layout):
    name = "tile"
    defaults = manager.Defaults(
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width.")
    )

    def __init__(self, ratio=0.618, masterWindows=1, expand=True,
        ratio_increment=0.05, add_on_top=True, shift_windows=False, **config):
        Layout.__init__(self, **config)
        self.clients = []
        self.ratio = ratio
        self.master = masterWindows
        self.focused = None
        self.expand = expand
        self.ratio_increment = ratio_increment
        self.add_on_top = add_on_top
        self.shift_windows = shift_windows

    @property
    def master_windows(self):
        return self.clients[:self.master]

    @property
    def slave_windows(self):
        return self.clients[self.master:]

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

    def focus_next(self, win):
        idx = self.clients.index(win)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_prev(self, win):
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx - 1]

    def get_next_index(self, currentindex):
        nextindex = currentindex + 1
        if nextindex >= len(self.clients):
            nextindex = 0
        return nextindex

    def get_previous_index(self, currentindex):
        previndex = currentindex - 1
        if previndex < 0:
            previndex = len(self.clients) - 1
        return previndex

    def getNextClient(self):
        currentindex = self.clients.index(self.focused)
        nextindex = self.get_next_index(currentindex)
        return self.clients[nextindex]

    def getPreviousClient(self):
        currentindex = self.clients.index(self.focused)
        previndex = self.get_previous_index(currentindex)
        return self.clients[previndex]

    def next(self):
        n = self.getPreviousClient()
        self.group.focus(n, True)

    def previous(self):
        n = self.getNextClient()
        self.group.focus(n, True)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll(True)

    def shift(self, idx1, idx2):
        if self.clients:
            self.clients[idx1], self.clients[idx2] = \
                self.clients[idx2], self.clients[idx1]
            self.group.layoutAll(True)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, c):
        self.focused = c

    def blur(self):
        self.focused = None

    def add(self, c):
        index = 0
        if not self.add_on_top and self.clients and self.focused:
            index = self.clients.index(self.focused)
        self.clients.insert(index, c)

    def remove(self, c):
        if self.focused is c:
            self.focused = None
        self.clients.remove(c)
        if self.clients and c is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, c, screen):
        screenWidth = screen.width
        screenHeight = screen.height
        x = y = w = h = 0
        borderWidth = self.border_width
        if self.clients and c in self.clients:
            pos = self.clients.index(c)
            if c in self.master_windows:
                w = (int(screenWidth * self.ratio) \
                         if len(self.slave_windows) or not self.expand \
                         else screenWidth)
                h = screenHeight / self.master
                x = screen.x
                y = screen.y + pos * h
            else:
                w = screenWidth - int(screenWidth * self.ratio)
                h = screenHeight / (len(self.slave_windows))
                x = screen.x + int(screenWidth * self.ratio)
                y = screen.y + self.clients[self.master:].index(c) * h
            if c is self.focused:
                bc = self.group.qtile.colorPixel(self.border_focus)
            else:
                bc = self.group.qtile.colorPixel(self.border_normal)
            c.place(
                x,
                y,
                w - borderWidth * 2,
                h - borderWidth * 2,
                borderWidth,
                bc,
                )
            c.unhide()
        else:
            c.hide()

    def info(self):
        return dict(
            all=[c.name for c in self.clients],
            master=[c.name for c in self.master_windows],
            slave=[c.name for c in self.slave_windows],
            )

    def cmd_down(self):
        self.down()

    def cmd_up(self):
        self.up()

    def cmd_next(self):
        self.next()

    def cmd_previous(self):
        self.previous()

    def cmd_decrease_ratio(self):
        self.ratio -= self.ratio_increment
        self.group.layoutAll()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layoutAll()

    def cmd_decrease_nmaster(self):
        self.master -= 1
        if self.master <= 0:
            self.master = 1
        self.group.layoutAll()

    def cmd_increase_nmaster(self):
        self.master += 1
        self.group.layoutAll()
