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

    def up(self):
        self.shuffle(utils.shuffleUp)

    def down(self):
        self.shuffle(utils.shuffleDown)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()
    
    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, c):
        self.clients.insert(0, c) #TODO: maybe make this configurable
                                  # Should new clients go to top?
        
    def remove(self, c):
        self.clients.remove(c)
        if self.clients:
            return self.clients[0] #TODO: figure this out
                                   #should the top get focus?
        else:
            return None
        #A better way. implement focus(), record which has focus, return this

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
            borderColor = self.theme["tile_border_normal"]
            colormap = self.group.qtile.display.screen().default_colormap
            bc = colormap.alloc_named_color(borderColor).pixel
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
                

    def cmd_down(self):
        self.down()

    def cmd_up(self):
        self.up()

    
