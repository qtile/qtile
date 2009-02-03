from base import SubLayout, Rect
from sublayouts import HorizontalStack
from subtile import SubTile

class SubVertTile(SubTile):
    arrangements = ["top", "bottom"]
    
    def _init_sublayouts(self):
        ratio = self.ratio
        expand = self.expand
        master_windows = self.master_windows
        arrangement = self.arrangement

        class MasterWindows(HorizontalStack):
            def filter(self, client):
                return self.index_of(client) < master_windows
            def request_rectangle(self, r, windows):
                return (r, Rect())

        class SlaveWindows(HorizontalStack):
            def filter(self, client):
                return self.index_of(client) >= master_windows
            def request_rectangle(self, r, windows):
                if self.autohide and not windows:
                    return (Rect(), r)
                else:
                    if arrangement == "top":
                        rmaster, rslave = r.split_horizontal(ratio=ratio)
                    else:
                        rslave, rmaster = r.split_horizontal(ratio=(1-ratio))
                    return (rslave, rmaster)
        
        self.sublayouts.append(SlaveWindows(self.clientStack,
                                            self.theme,
                                            parent=self,
                                            autohide=self.expand
                                            )
                               )
        self.sublayouts.append(MasterWindows(self.clientStack,
                                             self.theme,
                                             parent=self,
                                             autohide=self.expand
                                             )
                               )
                            
