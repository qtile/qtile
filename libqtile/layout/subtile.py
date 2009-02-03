from clientstack import ClientStack
from base import SubLayout, Rect
from sublayouts import VerticalStack


class SubTile(SubLayout):
    arrangements = ["left", "right"]
    def __init__(self, clientStack, theme, parent=None, autohide=True, master_windows=1, ratio=0.618, arrangement="left", expand=True):
        self.master_windows = master_windows
        self.ratio = ratio
        self.arrangement = (arrangement if arrangement in self.arrangements else self.arrangements[0])
        self.expand = expand
        SubLayout.__init__(self, clientStack, theme, parent, autohide)

    def _init_sublayouts(self):
        # these classes may want some variables
        ratio = self.ratio
        expand = self.expand
        master_windows = self.master_windows
        arrangement = self.arrangement

        class MasterWindows(VerticalStack):
            def filter(self, client):
                return self.index_of(client) < master_windows
            def request_rectangle(self, r, windows):
                #just take the lot, since this is called AFTER slave windows
                # - let the slaves take what they want, we'll have the rest
                return (r, Rect())

        class SlaveWindows(VerticalStack):
            def filter(self, client):
                return self.index_of(client) >= master_windows
            def request_rectangle(self, r, windows):
                if self.autohide and len(windows) == 0:
                    return (Rect(), r)
                else:
                    if arrangement == "left":
                        rmaster, rslave = r.split_vertical(ratio=ratio)
                    else:
                        rslave, rmaster = r.split_vertical(ratio=(1-ratio))
                    return (rslave, rmaster)
            
        self.sublayouts.append(SlaveWindows(self.clientStack,
                                            self.theme,
                                            parent=self,
                                            autohide=self.expand,
                                            )
                               )
        self.sublayouts.append(MasterWindows(self.clientStack,
                                             self.theme,
                                             parent=self,
                                             autohide=False
                                             )
                               )
                   
    def filter(self, client):
        return True #TAKE THEM ALL

    def request_rectangle(self, rectangle, windows):
        #        rectangle I want           rectangle left = NOTHING!!
        return (rectangle, Rect())
        
            
        
        
                     
