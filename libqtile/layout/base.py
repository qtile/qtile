# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import copy, sys
from .. import command

class Layout(command.CommandObject):
    """
        This class defines the API that should be exposed by all layouts.
    """
    def layout(self, windows):
        for i in windows:
            self.configure(i)

    def clone(self, group, theme):
        """
            :group Group to attach new layout instance to.

            Make a copy of this layout. This is done to provide each group with
            a unique instance of every layout.
        """
        c = copy.copy(self)
        c.group = group
        c.theme = theme
        return c

    def focus(self, c):
        """
            Called whenever the focus changes.
        """
        pass

    def add(self, c):
        """
            Called whenever a window is added to the group, whether the layout
            is current or not. The layout should just add the window to its
            internal datastructures, without mapping or configuring.
        """
        pass

    def remove(self, c):
        """
            Called whenever a window is removed from the group, whether the
            layout is current or not. The layout should just de-register the
            window from its data structures, without unmapping the window.

            Returns the "next" window that should gain focus or None.
        """
        pass

    def configure(self, c):
        """
            This method should:
                
                - Configure the dimensions and borders of a window using the
                  .place() method.
                - Call either .hide or .unhide on the window.
        """
        raise NotImplementedError

    def info(self):
        """
            Returns a dictionary of layout information.
        """
        return dict(
            name = self.name,
            group = self.group.name
        )

    def _items(self, name):
        if name == "screen":
            return True, None
        elif name == "group":
            return True, None

    def _select(self, name, sel):
        if name == "screen":
            return self.group.screen
        elif name == "group":
            return self.group

    def cmd_info(self):
        """
            Return a dictionary of info for this object.
        """
        return self.info()


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
        self.active_border = color(theme["%s_border_active" % name])
        self.focused_border = color(theme["%s_border_focus" % name])
        self.normal_border = color(theme["%s_border_normal" % name])
        self.border_width = theme["%s_border_width" % name]
            

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
            Define what rectangle this sublayout 'wants'. Don't be greedy.. well.. if you have to
            :rectangle - the total rectangle available. DON'T BE GREEDY!
            :windows - the windows that will be layed out with this - so you can know if you're gonna not have anything to lay out
            The last sublayout to lay out won't get a choice - they'll get whatever's left
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
                rect, rect_remaining = sl.request_rectangle(rectangle, 
                                                              filtered)
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
        bc = (self.focused_border \
                  if self.clientStack.focus_history \
                  and self.clientStack.focus_history[0] is client \
                  else self.normal_border
              )
        client.place(x,
                     y,
                     w - 2*self.border_width,
                     h - 2*self.border_width,
                     self.border_width,
                     bc
                     )
        client.unhide()
