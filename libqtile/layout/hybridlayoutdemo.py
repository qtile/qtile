from base import SubLayout, Rect
from sublayouts import VerticalStack, Floating
from subtile import SubTile

class HybridLayoutDemo(SubLayout):

    def _init_sublayouts(self):
        class TopWindow(VerticalStack):
            def filter_windows(self, windows):
                windows = [w for w in windows if w.name == "htop"]
                return ([windows[0],] if len(windows) else [])
            def request_rectangle(self, r, windows):
                if windows:
                    return r.split_horizontal(height=300)
                else:
                    return (Rect(0,0,0,0), r)

        self.sublayouts.append(Floating(self.clientStack,
                                        self.theme,
                                        parent=self,
                                        )
                               )
        self.sublayouts.append(TopWindow(self.clientStack,
                                         self.theme,
                                         parent=self,
                                         autohide=True,
                                         )
                               )
        self.sublayouts.append(SubTile(self.clientStack,
                                       self.theme,
                                       parent=self,
                                       master_windows = 2,
                                       )
                               )
    
    def filter(self, client):
        return True
