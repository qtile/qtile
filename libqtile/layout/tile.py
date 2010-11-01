from base import Layout
from .. import utils, manager

class Tile(Layout):
    name="tile"
    defaults = manager.Defaults(
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width.")
    )
    def __init__(self, ratio=0.618, masterWindows=1, expand=True,
        ratio_increment=0.05, **config):
        Layout.__init__(self, **config)
        self.clients = []
        self.ratio = ratio
        self.master = masterWindows
        self.focused = None
        self.expand = expand
        self.ratio_increment = ratio_increment

    @property
    def master_windows(self):
        return self.clients[:self.master]

    @property
    def slave_windows(self):
        return self.clients[self.master:]

    def up(self):
        self.shuffle(utils.shuffleUp)

    def down(self):
        self.shuffle(utils.shuffleDown)

    def getNextClient(self):
        nextindex = self.clients.index(self.focused) + 1
        if nextindex >= len(self.clients):
            nextindex = 0
        return self.clients[nextindex]

    def getPreviousClient(self):
        previndex = self.clients.index(self.focused) - 1
        if previndex < 0:
            previndex = len(self.clients) - 1;
        return self.clients[previndex]

    def next(self):
        n = self.getPreviousClient()
        self.group.focus(n, True)
        self.focus(n)

    def previous(self):
        n = self.getNextClient()
        self.group.focus(n, True)
        self.focus(n)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, c):
        self.focused = c

    def add(self, c):
        self.clients.insert(0, c) #TODO: maybe make this configurable
                                  # Should new clients go to top?
        if len(self.clients) == 1:
            self.group.focus(c, True)
            self.focus(c)

    def remove(self, c):
        self.clients.remove(c)
        if self.clients and c is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, c):
        screenWidth = self.group.screen.dwidth
        screenHeight = self.group.screen.dheight
        x = y = w = h = 0
        borderWidth = self.border_width
        if self.clients and c in self.clients:
            pos = self.clients.index(c)
            if c in self.master_windows:
                w = (int(screenWidth*self.ratio) \
                         if len(self.slave_windows) or not self.expand \
                         else screenWidth)
                h = screenHeight/self.master
                x = self.group.screen.dx
                y = self.group.screen.dy + pos*h
            else:
                w = screenWidth-int(screenWidth*self.ratio)
                h = screenHeight/(len(self.slave_windows))
                x = self.group.screen.dx + int(screenWidth*self.ratio)
                y = self.group.screen.dy + self.clients[self.master:].index(c)*h
            if c is self.focused:
                bc = self.group.qtile.colorPixel(self.border_focus)
            else:
                bc = self.group.qtile.colorPixel(self.border_normal)
            c.place(
                x,
                y,
                w-borderWidth*2,
                h-borderWidth*2,
                borderWidth,
                bc,
                )
            c.unhide()
        else:
            c.hide()

    def info(self):
        return dict(
            all = [c.name for c in self.clients],
            master = [c.name for c in self.master_windows],
            slave = [c.name for c in self.slave_windows],
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
        if self.master < 0:
            self.master += 1
        self.group.layoutAll()

    def cmd_increase_nmaster(self):
        self.master += 1
        self.group.layoutAll()
