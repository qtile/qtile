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
from ..theme import Theme

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
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    #TODO:
        # functions for splitting
        # functions for bordering??

class SubLayout:
    def __init__(self, clientStack, theme=Theme({})):
        self.clientStack = clientStack
        self.clients = []
        self.sublayouts = []
        self.theme = theme

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

    def layout_sublayouts(self, sublayouts_and_rects, windows):
        for sl, rect in sublayouts_and_rects:
            filtered_windows = [w for w in windows if sl.filter(w)]
            sl.layout(rect, filtered_windows)
            windows = [w for w in windows if w not in filtered_windows]
            

    def layout(self, rectangle, windows):
        """
           Layout the list of windows in the specified rectangle
           This should be overriden by any SubLayout that has SubLayouts of its own
           - don't send all sublayouts the same rectangle
        """
        if self.sublayouts:
            sls_and_rects = [(sl, rect) for sl in self.sublayouts]
            self.layout_sublayouts(sls_and_rects, windows)
        else:
            #TODO: refactor this - the list of windows should be filtered elsewhere
            for c in windows:
                if c in self.clients: #safety check
                    if self.filter(c):
                        self.configure(rectangle, c)
                
    def configure(self, client):
        """
            Place a window
        """
        raise NotImplementedError
        
