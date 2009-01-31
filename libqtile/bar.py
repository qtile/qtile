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

import sys
import manager, window, confreader, command, utils
import Xlib.X

_HIGHLIGHT = "#48677E"
_FOREGROUND = "#dddddd"

class Gap(command.CommandObject):
    def __init__(self, size):
        """
            :size The width of the gap.
        """
        self.size = size
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen, event, theme):
        self.qtile, self.screen, self.event, self.theme = qtile, screen, event, theme

    @property
    def x(self):
        s = self.screen
        if s.right is self:
            return s.dx + s.dwidth
        else:
            return s.x

    @property
    def y(self):
        s = self.screen
        if s.top is self:
            return s.y
        elif s.bottom is self:
            return s.dy + s.dheight
        elif s.left is self:
            return s.dy
        elif s.right is self:
            return s.y + s.dy

    @property
    def width(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return s.width
        else:
            return self.size

    @property
    def height(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return self.size
        else:
            return s.dheight

    def geometry(self):
        return self.x, self.y, self.width, self.height

    def _items(self, name):
        if name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    @property
    def position(self):
        for i in ["top", "bottom", "left", "right"]:
            if getattr(self.screen, i) is self:
                return i

    def info(self):
        return dict(
            position=self.position
        )

    def cmd_info(self):
        """
            Info for this object.
        """
        return self.info()


STRETCH = -1
class Bar(Gap):
    background = "black"
    widgets = None
    window = None
    def __init__(self, widgets, size):
        """
            Note that bars can only be at the top or the bottom of the screen.
            
            :widgets A list of widget objects.
            :size The width of the bar.
        """
        Gap.__init__(self, size)
        self.widgets = widgets

    def _configure(self, qtile, screen, event, theme):
        if not self in [screen.top, screen.bottom]:
            raise confreader.ConfigError("Bars must be at the top or the bottom of the screen.")
        Gap._configure(self, qtile, screen, event, theme)
        self.background = theme["bar_bg_normal"]
        colormap = qtile.display.screen().default_colormap
        c = colormap.alloc_named_color(self.background).pixel
        opacity = theme["bar_opacity"]
        self.window = window.Internal.create(
                        self.qtile,
                        c,
                        self.x, self.y, self.width, self.height,
                        opacity
                     )
        self.window.handle_Expose = self.handle_Expose
        self.window.handle_ButtonPress = self.handle_ButtonPress
        qtile.internalMap[self.window.window] = self.window
        self.window.unhide()

        for i in self.widgets:
            qtile.registerWidget(i)
            i._configure(qtile, self, event, theme)
        self.resize()

    def resize(self):
        offset = 0
        stretchWidget = None
        for i in self.widgets:
            i.offset = offset
            if i.width == STRETCH:
                stretchWidget = i
                break
            offset += i.width
        total = offset
        offset = self.width
        if stretchWidget:
            for i in reversed(self.widgets):
                if i.width == STRETCH:
                    break
                offset -= i.width
                total += i.width
                i.offset = offset
            stretchWidget.width = self.width - total

    def handle_Expose(self, e):
        self.draw()

    def handle_ButtonPress(self, e):
        for i in self.widgets:
            if e.event_x < i.offset + i.width:
                i.click(e.event_x - i.offset, e.event_y)
                break

    def draw(self):
        for i in self.widgets:
            i.draw()

    def info(self):
        return dict(
            position = self.position,
            widgets = [i.info() for i in self.widgets],
            window = self.window.window.id
        )

    def get(self, q, screen, position):
        if len(q.screens) - 1 < screen:
            raise command.CommandError("No such screen: %s"%screen)
        s = q.screens[screen]
        b = getattr(s, position)
        if not b:
            raise command.CommandError("No such bar: %s:%s"%(screen, position))
        return b

    def cmd_fake_click(self, screen, position, x, y):
        """
            Fake a mouse-click on the bar. Co-ordinates are relative 
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        class _fake: pass
        fake = _fake()
        fake.event_x = x
        fake.event_y = y
        self.handle_ButtonPress(fake)
