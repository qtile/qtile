from base import SubLayout, Rect
from Xlib import Xatom

class TopLevelSubLayout(SubLayout):
    '''
       This class effectively wraps a sublayout, and automatically adds a floating sublayout,
    '''
    def __init__(self, sublayout_data, clientStack, theme):
        WrappedSubLayout, args = sublayout_data
        SubLayout.__init__(self, clientStack, theme)
        self.sublayouts.append(Floating(clientStack,
                                        theme,
                                        parent=self
                                        )
                               )
        self.sublayouts.append(WrappedSubLayout(clientStack,
                                         theme,
                                         parent=self,
                                         **args
                                         )
                               )

class VerticalStack(SubLayout):
    def layout(self, rectangle, windows):
        SubLayout.layout(self, rectangle, windows)

    def configure(self, r, client):
        position = self.windows.index(client)
        cliheight = int(r.h / len(self.windows)) #inc border
        self.place(client,
                   r.x,
                   r.y + cliheight*position,
                   r.w,
                   cliheight,
                   )
                     

class Floating(SubLayout):
    def filter(self, client):
        window = client.window
        d = client.qtile.display
        floating = d.intern_atom('_NET_WM_WINDOW_TYPE_DIALOG')
        try:
            win_type = window.get_full_property(
                d.intern_atom('_NET_WM_WINDOW_TYPE'), 
                Xatom.ATOM
                )
        except:
            #bad window, no floating for you
            return False
        if not win_type:
            # window is without a type
            return False
        elif win_type.value[0] == floating:
            #yup, we want it
            return True
        else:
            # noop, it has a type, but not what we're after
            # TODO: handle dock windows??
            return False

    def request_rectangle(self, r, windows):
        return (Rect(0,0,0,0), r) #we want nothing

    def configure(self, r, client):
        client.unhide() #let it be where it wants

