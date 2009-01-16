from base import Layout
from .. import command, utils
from ..theme import Theme

class Magnify(Layout):
    name = "layout"
    def __init__(self, theme=Theme({}), gap=50):
        Layout.__init__(self)
        self.clients = []
        self.gap = gap
        self.theme = theme

    def up(self):
        self.shuffle(utils.shuffleUp)

    def down(self):
        self.shuffle(utils.shuffleDown)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], False)

    def close(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, c):
        if c in self.clients:
            pos = self.clients.index(c)
            self.clients[0], self.clients[pos] = \
                self.clients[pos], self.clients[0]
            self.group.layoutAll()

    def add(self, c):
        self.clients.insert(0, c)

    def remove(self, c):
        self.clients.remove(c)
        if self.clients: #still has items?
            return self.clients[0] #return next focus
        else:
            return None #no more focus :(

    def configure(self, c):
        """
            places the window appropriately
            place(self, x, y, width, height, border, borderColor)
            First window is centre of screen (index 0)
            Others stack behind it (indices 1 +)
            
        """
        screenWidth = self.group.screen.dwidth
        screenHeight = self.group.screen.dheight
        gap = self.gap
        x = y = w = h = 0
        borderWidth = self.theme["border_width"]
        if self.clients and c in self.clients:
            if c is self.clients[0]:
                x = self.group.screen.dx + gap
                y = self.group.screen.dy + gap
                w = screenWidth - 2*gap
                h = screenHeight - 2*gap
                borderColor = self.theme["border_focus"]
            else:
                clis = self.clients[1:]
                position = clis.index(c)
                w = screenWidth
                h = screenHeight/len(clis) #TODO: CAST TO INT?
                x = self.group.screen.dx
                y = self.group.screen.dy + position*h
                borderColor = self.theme["border_normal"]
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
        """
           Switch down in the window list
        """
        self.down()

    def cmd_up(self):
        """
           Switch up...
        """
        self.up()
                
