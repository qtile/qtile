from clientstack import ClientStack
from base import SubLayout, Rect
from sublayouts import VerticalStack


class TileTwo(SubLayout):
    def __init__(self, clientStack, theme, master_windows=1, ratio=0.618):
        SubLayout.__init__(self, clientStack, theme)
        self.master_windows = master_windows
        self.ratio = ratio
        self.sublayouts = []

        class MasterWindows(VerticalStack):
            def filter(self, client):
                return self.clientStack.index_of(client) < master_windows

        class SlaveWindows(VerticalStack):
            def filter(self, client):
                return self.clientStack.index_of(client) >= master_windows
            
        for SL in [MasterWindows, SlaveWindows]:
            self.sublayouts.append(SL(clientStack,
                                      theme,
                                      ))
    def filter(self, client):
        return True #TAKE THEM ALL

    def layout(self, r, windows):
        master = Rect(r.x, r.y, int(r.w * self.ratio), r.h)
        slave = Rect(r.x+int(r.w*self.ratio), r.y, int(r.w * (1 - self.ratio)), r.h)
        self.layout_sublayouts([(self.sublayouts[0], master), (self.sublayouts[1], slave)], windows)
            
        
        
                     
