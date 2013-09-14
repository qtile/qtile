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

import command

class Gap(command.CommandObject):
    """
        A gap, placed along one of the edges of the screen. If a gap has been
        defined, Qtile will avoid covering it with windows. The most probable
        reason for configuring a gap is to make space for a third-party bar or
        other static window.
    """
    def __init__(self, size):
        """
            size: The width of the gap.
        """
        self.size = size
        self.qtile = None
        self.screen = None

    def _configure(self, qtile, screen):
        self.qtile = qtile
        self.screen = screen

    def draw(self):
        pass

    @property
    def x(self):
        screen = self.screen
        if screen.right is self:
            return screen.dx + screen.dwidth
        else:
            return screen.x

    @property
    def y(self):
        screen = self.screen
        if screen.top is self:
            return screen.y
        elif screen.bottom is self:
            return screen.dy + screen.dheight
        elif screen.left is self:
            return screen.dy
        elif screen.right is self:
            return screen.y + screen.dy

    @property
    def width(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return screen.width
        else:
            return self.size

    @property
    def height(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return self.size
        else:
            return screen.dheight

    def geometry(self):
        return (self.x, self.y, self.width, self.height)

    def _items(self, name):
        if name == "screen":
            return (True, None)

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    @property
    def position(self):
        for i in ["top", "bottom", "left", "right"]:
            if getattr(self.screen, i) is self:
                return i

    def info(self):
        return dict(position=self.position)

    def cmd_info(self):
        """
            Info for this object.
        """
        return self.info()

