from clientstack import ClientStack
from base import SubLayout, Rect

class MasterWindows(SubLayout):
    def __init__(self, clientStack, theme, master_windows):
        SubLayout.__init__(self, 
                           clientStack, 
                           theme
                           )
        self.master_windows = master_windows
        
    def filter(self, client):
        print "in should_add for masterwindows"
        print "self.layout has id", id(self.layout)
        adding = self.clientStack.index_of(client) < self.master_windows
        print "shall add the client: %s" % adding
        return adding

    def configure(self, r, client):
        print "masterwindows, moving to", r.x, r.y, r.w, r.h
        client.place(r.x,
                     r.y,
                     r.w,
                     r.h,
                     0,
                     0,
                     )
        client.unhide()

      
class SlaveWindows(SubLayout):
    def __init__(self, clientStack, theme, master_windows):
        SubLayout.__init__(self,
                           clientStack,
                           theme)
        self.master_windows = master_windows

    def filter(self, client):
        return self.clientStack.index_of(client) >= self.master_windows

    def configure(self, r, client):
        print "slavewindows, moving to", r.x, r.y, r.w, r.h
        client.place(r.x,
                     r.y,
                     r.w,
                     r.h,
                     0,
                     0
                     )
        client.unhide()
    

class TileTwo(SubLayout):
    def __init__(self, clientStack, theme, master_windows=1, ratio=0.618):
        SubLayout.__init__(self, clientStack, theme)
        print "self.clientStack is", self.clientStack
        self.master_windows = master_windows
        self.ratio = ratio
        self.sublayouts = []
        for SL in [MasterWindows, SlaveWindows]:
            self.sublayouts.append(SL(clientStack,
                                      theme,
                                      master_windows
                                      ))
    def filter(self, client):
        print "Calling should_add for tiletwo"
        return True #TAKE THEM ALL

    def layout(self, r, windows):
        print "rectangle given is"
        print r.x
        print r.y
        print r.w
        print r.h
        master = Rect(r.x, r.y, int(r.w * self.ratio), r.h)
        slave = Rect(r.x+int(r.w*self.ratio), r.y, int(r.w * (1 - self.ratio)), r.h)
        self.sublayouts[0].layout(master, windows)
        self.sublayouts[1].layout(slave, windows)
            
        
        
                     
