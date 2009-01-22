from clientstack import ClientStack
from base import SubLayout, Rect
from sublayouts import VerticalStack


class TileTwo(SubLayout):
    def __init__(self, clientStack, theme, master_windows=1, ratio=0.618, expand=True):
        SubLayout.__init__(self, clientStack, theme)
        self.master_windows = master_windows
        self.ratio = ratio
        self.expand = expand
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
        master_windows = [w for w in windows if self.sublayouts[0].filter(w)]
        slave_windows = [w for w in windows if w not in master_windows]
        # rectangles 
        master = Rect(r.x, 
                      r.y, 
                      (int(r.w * self.ratio) if len(slave_windows) or not self.expand else r.w), 
                      r.h)
        slave = Rect(r.x+int(r.w*self.ratio), r.y, int(r.w * (1 - self.ratio)), r.h)
        self.sublayouts[0].layout(master, master_windows)
        self.sublayouts[1].layout(slave, slave_windows)
            
        
        
                     
