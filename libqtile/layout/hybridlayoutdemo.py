from base import SubLayout, Rect
from sublayouts import VerticalStack
from tiletwo import TileTwo

class HybridLayoutDemo(SubLayout):
    def __init__(self, clientStack, theme):
        SubLayout.__init__(self, clientStack, theme)
        class TopWindow(VerticalStack):
            def filter(self, client):
                return client.name == "special"
        self.sublayouts.append(TopWindow(clientStack,
                                         theme
                                         ))
        self.sublayouts.append(TileTwo(clientStack,
                                       theme,
                                       master_windows=2
                                       ))
    def filter(self, client):
        return True
    
    def layout(self, r, windows):
        top_rect = Rect(r.x,
                        r.y,
                        r.w,
                        150)
        bottom_rect = Rect(r.x,
                           r.y + 150,
                           r.w,
                           r.h - 150)
        layouts_and_rects = zip(self.sublayouts, [top_rect, bottom_rect])
        self.layout_sublayouts(layouts_and_rects, windows)
                                  
