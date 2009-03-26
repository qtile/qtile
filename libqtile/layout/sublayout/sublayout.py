from Xlib import Xatom

class Rect:
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def split_vertical(self, ratio=0.5, width=None):
        if not width:
            width = int(ratio*self.w)
        if width > self.w:
            raise Exception, "You're trying to take too much of the rectangle"
        return (Rect(self.x,
                     self.y,
                     width,
                     self.h),
                Rect(self.x + width,
                     self.y,
                     self.w - width,
                     self.h)
                )
    
    def split_horizontal(self, ratio=0.5, height=None):
        if not height:
            height = int(ratio*self.h)
        if height > self.h:
            raise Exception, "You're trying to take too much of this rectange"
        return (Rect(self.x,
                     self.y,
                     self.w,
                     height),
                Rect(self.x,
                     self.y + height,
                     self.w,
                     self.h - height)
                )
    

    def __repr__(self):
        return "(%s, %s, %s, %s)" % (self.x, self.y, self.w, self.h)


class SubLayout:
    def __init__(self, clientStack, theme, parent=None, autohide=True):
        """
           autohide - does it hide itself if there are no clients
        """
        self.clientStack = clientStack
        self.clients = []
        self.sublayouts = []
        self.theme = theme
        self.parent = parent
        self.autohide = autohide
        self.windows = []
        self._init_sublayouts()
        self.active_border = None
    
    def _init_bordercolors(self):
        colormap = self.clientStack.group.qtile.display.screen().default_colormap
        color = lambda color: colormap.alloc_named_color(color).pixel
        name = self.__class__.__name__.lower()
        theme = self.theme
        self.active_border = color(theme.border_active)
        self.focused_border = color(theme.border_focus)
        self.normal_border = color(theme.border_normal)
        self.border_width = theme.border_width

    def _init_sublayouts(self):
        """
           Define sublayouts here, and so, only override init if you really must
        """
        pass

    def filter_windows(self, windows):
        return [w for w in windows if self.filter(w)]

    def filter(self, client):
        raise NotImplementedError

    def add(self, client):
        """
            Receives a client that this SubLayout may be interested in.
        """
        self.clients.append(client) #keep a copy regardless
        if self.sublayouts:
            for sl in self.sublayouts:
                sl.add(client)


    def focus(self, client):
        """
           Some client in the ClientStack got focus, no clue if it concerns us
        """

    def remove(self, client):
        if client in self.clients:
            self.clients.remove(client)

    def request_rectangle(self, rectangle, windows):
        """

            Define what rectangle this sublayout 'wants'. Don't be greedy..
            well.. if you have to

            :rectangle - the total rectangle available. DON'T BE GREEDY!
            :windows - the windows that will be layed out with this - so you
            can know if you're gonna not have anything to lay out

            Return a tuple containing the rectangle you want, and the rectangle that's left.
        """
        raise NotImplementedError

    def layout(self, rectangle, windows):
        """
           Layout the list of windows in the specified rectangle
        """
        self.windows = windows
        # setup colors
        if not self.active_border:
            self._init_bordercolors()
        # done
        if self.sublayouts:
            sls = []
            for sl in self.sublayouts:
                filtered = sl.filter_windows(windows)
                rect, rect_remaining = sl.request_rectangle(rectangle, filtered)
                sls.append((sl, rect, filtered))
                rectangle = rect_remaining
                windows = [w for w in windows if w not in filtered]
            for sl, rect, clients in sls:
                sl.layout(rect, clients)
            
        else:
            for c in self.windows:
                self.configure(rectangle, c)

    def index_of(self, client):
        if self.parent:
            return self.parent.windows.index(client)
        else:
            return self.clientStack.index_of(client)

    def configure(self, rectangle, client):
        """
            Place a window
        """
        raise NotImplementedError, "this is %s" % self.__class__.__name__

    def place(self, client, x, y, w, h):
        bc, opacity = ((self.focused_border, 1.0) \
                  if self.clientStack.focus_history \
                  and self.clientStack.focus_history[0] is client \
                  else (self.normal_border, 0.5)
              )
        client.place(x,
                     y,
                     w - 2*self.border_width,
                     h - 2*self.border_width,
                     self.border_width,
                     bc
                     )
        client.unhide()
        client.opacity = opacity

    def command_get_arg(self, args, kwargs, name, default):
        if name in kwargs:
            return kwargs['name']
        elif args:
            if name < len(args):
                return args[name]
            else:
                return args[0]
        else:
            return default
        

    def command(self, mask, command, *args, **kwargs):
        def split_command(command):
            parts = command.split('_')
            if len(parts) > 1:
                mask = parts[0]
                com = '_'.join(parts[1:])
            else:
                mask = '*'
                com = '_'.join(parts)
            return (mask, com)
            
        for sl in self.sublayouts:
            if mask == '*':
                sl.command(mask, command, *args, **kwargs)
            elif mask == '?':
                ma, com = split_command(command)
                self.command(ma, com, *args, **kwargs)
            elif mask == sl.__class__.__name__:
                ma, com = split_command(command)
                self.comand(ma, com, *args, **kwargs)
            else:
                print >> sys.stderr, "command ('%s' '%s') not passed on" % (mask, command)

class TopLevelSubLayout(SubLayout):
    '''
       This class effectively wraps a sublayout, and automatically adds a floating sublayout,
    '''
    def __init__(self, sublayout_data, clientStack, theme):
        WrappedSubLayout, args = sublayout_data
        SubLayout.__init__(self, clientStack, theme)
        self.sublayouts.append(Minimised(clientStack,
                                         theme,
                                         parent=self
                                         )
                               )
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
      
               
class HorizontalStack(SubLayout):
    def configure(self, r, client):
        position = self.windows.index(client)
        cliwidth = int(r.w / len(self.windows))
        self.place(client,
                   r.x + cliwidth*position,
                   r.y,
                   cliwidth,
                   r.h
                   )


class Floating(SubLayout):
    def filter(self, client):
        return client.floating

    def request_rectangle(self, r, windows):
        return (Rect(), r) #we want nothing

    def configure(self, r, client):
        d = client.floatDimensions
        self.place(client, **d)


class Minimised(SubLayout):
    def filter(self, client):
        return client.minimised

    def request_rectangle(self, r, windows):
        return (Rect(), r) #we want nothing
    
    def configure(self, r, client):
        client.hide()
