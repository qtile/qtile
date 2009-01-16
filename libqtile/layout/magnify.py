from base import Layout
from .. import command, utils

class Magnify(Layout):
    name = "layout"
    def __init__(self):
        Layout.__init__(self)
        self.clients = []

    def close(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

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
        """
        print "Trying to configure a client"
        print c.info()
        print "info printed"
        width = self.group.screen.dwidth
        height = self.group.screen.dheight
        gap = 50
        print "before if"
        if self.clients and c is self.clients[0]:
            print "yeah, it's the one"
            x = self.group.screen.dx + gap
            y = self.group.screen.dy + gap
            wi = width - 2*gap
            he = height - 2*gap
            print ("items", x, y, wi, he)
            c.place(
                self.group.screen.dx + gap,
                self.group.screen.dy + gap,
                width - 2*gap,
                height - 2*gap,
                0,
                None
                )
            c.unhide()
        else:
            print "else"
            print self.clients
            c.hide()
                
