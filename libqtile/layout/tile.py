from base import Layout
from .. import command, utils
from ..theme import Theme

class Tile(Layout):
    name="tile"
    def __init__(self, theme=Theme({}), ratio=0.618, masterWindows = 1):
        Layout.__init__(self)
        self.clients = []
        self.theme = theme
        self.ratio = ratio
        self.master = masterWindows
        self.focused = None
        # border colors get set in clone
        self.focusedBorder = None
        self.normalBorder = None

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

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()
    
    def clone(self, group):
        if not self.focusedBorder:
            colormap = group.qtile.display.screen().default_colormap
            self.focusedBorder = colormap.alloc_named_color(
                self.theme["tile_border_focus"],
                ).pixel
            self.normalBorder = colormap.alloc_named_color(
                self.theme["tile_border_normal"],
                ).pixel
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, c):
        self.focused = c

    def add(self, c):
        self.clients.insert(0, c) #TODO: maybe make this configurable
                                  # Should new clients go to top?
        
    def remove(self, c):
        self.clients.remove(c)
        if self.clients and c is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, c):
        screenWidth = self.group.screen.dwidth
        screenHeight = self.group.screen.dheight
        x = y = w = h = 0
        borderWidth = self.theme["tile_border_width"]
        if self.clients and c in self.clients:
            pos = self.clients.index(c)
            if c in self.clients[:self.master]:
                w = int(screenWidth*self.ratio)
                h = screenHeight/self.master
                x = self.group.screen.dx
                y = self.group.screen.dy + pos*h
            else:
                w = int(screenWidth*(1-self.ratio))
                h = screenHeight/(len(self.clients[self.master:]))
                x = self.group.screen.dx + int(screenWidth*self.ratio)
                y = self.group.screen.dy + self.clients[self.master:].index(c)*h
            if c is self.focused:
                bc = self.focusedBorder
            else:
                bc = self.normalBorder
            c.place(
                x,
                y,
                w,
                h,
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

    
