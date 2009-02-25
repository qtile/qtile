from clientstack import ClientStack
from sublayout import VerticalStack, SubLayout, Rect


class SubTile(SubLayout):
    arrangements = ["left", "right"]
    def __init__(self, clientStack, theme, parent=None, autohide=True, master_windows=1, ratio=0.618, arrangement="left", expand=True):
        self.master_windows = master_windows
        self.ratio = ratio
        self.arrangement = (arrangement if arrangement in self.arrangements else self.arrangements[0])
        self.expand = expand
        SubLayout.__init__(self, clientStack, theme, parent, autohide)

    def _init_sublayouts(self):
        class MasterWindows(VerticalStack):
            def filter(self, client):
                return self.index_of(client) < self.parent.master_windows
            def request_rectangle(self, r, windows):
                #just take the lot, since this is called AFTER slave windows
                # - let the slaves take what they want, we'll have the rest
                return (r, Rect())

        class SlaveWindows(VerticalStack):
            def filter(self, client):
                return self.index_of(client) >= self.parent.master_windows
            def request_rectangle(self, r, windows):
                if self.autohide and len(windows) == 0:
                    return (Rect(), r)
                else:
                    if self.parent.arrangement == "left":
                        rmaster, rslave = r.split_vertical(ratio=self.parent.ratio)
                    else:
                        rslave, rmaster = r.split_vertical(ratio=(1-self.parent.ratio))
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

    def command(self, mask, command, *args, **kwargs):
        if command == 'ratio':
            ratio = self.command_get_arg(args, kwargs, 'ratio', self.ratio)
            self.ratio = ratio
            self.clientStack.group.layoutAll()
        elif command == 'incratio':
            incr = self.command_get_arg(args, kwargs, 'incr', 0.1)
            self.ratio += incr
            if self.ratio < 0: self.ratio = 0
            if self.ratio > 1: self.ratio = 1.0
            self.clientStack.group.layoutAll()
        elif command == 'incnmaster':
            incr = self.command_get_arg(args, kwargs, 'incr', 1)
            self.master_windows += incr
            if self.master_windows < 1:
                self.master_windows = 1 #don't let it drop below one - not set up to cope with this yet
            self.clientStack.group.layoutAll()
        elif command == 'nextarrangement':
            self.arrangement = self.arrangements[(self.arrangements.index(self.arrangement) + 1) % len(self.arrangements)]
            self.clientStack.group.layoutAll()
        SubLayout.command(self, mask, command, *args, **kwargs)
        
            
        
        
                     
