from base import Layout
from .. import command, utils

class Magnify(Layout):
    name = "layout"
    def __init__(self, gap=50):
        Layout.__init__(self)
        self.clients = []
        self.gap = gap
        self.focusedBorder = None
        self.normalBorder = None
    def up(self):
        self.shuffle(utils.shuffleUp)

    def down(self):
        self.shuffle(utils.shuffleDown)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], True)

    def clone(self, group, theme):
        if not self.focusedBorder:
            colormap = group.qtile.display.screen().default_colormap
            self.focusedBorder = colormap.alloc_named_color(
                theme["magnify_border_focus"],
                ).pixel
            self.normalBorder = colormap.alloc_named_color(
                theme["magnify_border_normal"],
                ).pixel
        c = Layout.clone(self, group, theme)
        c.clients = []
        return c

    def focus(self, c):
        '''
        Don't allow anything apart from the chosen one (self.clients[0]) get any focus
        '''
        if c in self.clients and c is self.clients[0]:
            return
        else:
            self.group.focus(self.clients[0], False)
        #no need to call layoutAll, focus already does that

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
        borderWidth = self.theme["magnify_border_width"]
        if self.clients and c in self.clients:
            if c is self.clients[0]:
                x = self.group.screen.dx + gap
                y = self.group.screen.dy + gap
                w = screenWidth - 2*gap
                h = screenHeight - 2*gap
                bc = self.focusedBorder
            else:
                clis = self.clients[1:]
                position = clis.index(c)
                w = screenWidth
                h = screenHeight/len(clis) #TODO: CAST TO INT?
                x = self.group.screen.dx
                y = self.group.screen.dy + position*h
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
        return [i.name for i in self.clients]

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
                
