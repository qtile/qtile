# Copyright (c) 2014, Florian Scherf <fscherf@gmx.net>. All rights reserved.
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

from __future__ import division

from .base import Layout


class VerticalTile(Layout):
    """Tiling layout that works nice on vertically mounted monitors

    The available height gets divided by the number of panes, if no pane is
    maximized. If one pane has been maximized, the available height gets split
    in master- and secondary area. The maximized pane (master pane) gets the
    full height of the master area and the other panes (secondary panes) share
    the remaining space.  The master area (at default 75%) can grow and shrink
    via keybindings.

    ::

        -----------------                -----------------  ---
        |               |                |               |   |
        |       1       |  <-- Panes     |               |   |
        |               |        |       |               |   |
        |---------------|        |       |               |   |
        |               |        |       |               |   |
        |       2       |  <-----+       |       1       |   |  Master Area
        |               |        |       |               |   |
        |---------------|        |       |               |   |
        |               |        |       |               |   |
        |       3       |  <-----+       |               |   |
        |               |        |       |               |   |
        |---------------|        |       |---------------|  ---
        |               |        |       |       2       |   |
        |       4       |  <-----+       |---------------|   |  Secondary Area
        |               |                |       3       |   |
        -----------------                -----------------  ---

    Normal behavior. No              One maximized pane in the master area
    maximized pane. No               and two secondary panes in the
    specific areas.                  secondary area.

    ::

        -----------------------------------  In some cases VerticalTile can be
        |                                 |  useful on horizontal mounted
        |                1                |  monitors two.
        |                                 |  For example if you want to have a
        |---------------------------------|  webbrowser and a shell below it.
        |                                 |
        |                2                |
        |                                 |
        -----------------------------------


    Suggested keybindings:

    ::

        Key([modkey], 'j', lazy.layout.down()),
        Key([modkey], 'k', lazy.layout.up()),
        Key([modkey], 'Tab', lazy.layout.next()),
        Key([modkey, 'shift'], 'Tab', lazy.layout.next()),
        Key([modkey, 'shift'], 'j', lazy.layout.shuffle_down()),
        Key([modkey, 'shift'], 'k', lazy.layout.shuffle_up()),
        Key([modkey], 'm', lazy.layout.maximize()),
        Key([modkey], 'n', lazy.layout.normalize()),
    """

    defaults = [
        ('border_focus', '#FF0000', 'Border color for the focused window.'),
        ('border_normal', '#FFFFFF', 'Border color for un-focused windows.'),
        ('border_width', 1, 'Border width.'),
        ('margin', 0, 'Border margin.'),
        ('name', 'VerticalTile', 'Name of this layout.'),
    ]

    ratio = 0.75
    steps = 0.05

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(self.defaults)
        self.clients = []
        self.focused = None
        self.maximized = None

    def add(self, window):
        if self.clients and self.focused:
            index = self.clients.index(self.focused)
            self.clients.insert(index + 1, window)
        else:
            self.clients.append(window)

        self.focus(window)

    def remove(self, window):
        if window not in self.clients:
            return

        index = self.clients.index(window)
        self.clients.remove(window)

        if not self.clients:
            self.focused = None
            self.maximized = None
            return

        if self.maximized is window:
            self.maximized = None

        if index == len(self.clients):
            index -= 1

        self.focus(self.clients[index])
        return self.focused

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        c.focused = None
        return c

    def configure(self, window, screen):
        if self.clients and window in self.clients:
            n = len(self.clients)
            index = self.clients.index(window)

            # border
            if n > 1:
                border_width = self.border_width
            else:
                border_width = 0

            if window is self.focused:
                border_color = self.group.qtile.colorPixel(self.border_focus)
            else:
                border_color = self.group.qtile.colorPixel(self.border_normal)

            # width
            if n > 1:
                width = screen.width - self.border_width * 2
            else:
                width = screen.width

            # height
            if n > 1:
                main_area_height = int(screen.height * self.ratio)
                sec_area_height = screen.height - main_area_height

                main_pane_height = main_area_height - border_width * 2
                sec_pane_height = sec_area_height // (n - 1) - border_width * 2
                normal_pane_height = (screen.height // n) - (border_width * 2)

                if self.maximized:
                    if window is self.maximized:
                        height = main_pane_height
                    else:
                        height = sec_pane_height
                else:
                    height = normal_pane_height
            else:
                height = screen.height

            # y
            y = screen.y

            if n > 1:
                if self.maximized:
                    y += (index * sec_pane_height) + (border_width * 2 * index)
                else:
                    y += (index * normal_pane_height) +\
                        (border_width * 2 * index)

                if self.maximized and window is not self.maximized:
                    if index > self.clients.index(self.maximized):
                        y = y - sec_pane_height + main_pane_height

            window.place(screen.x, y, width, height, border_width,
                         border_color, margin=self.margin)
            window.unhide()
        else:
            window.hide()

    def blur(self):
        self.focused = None

    def focus(self, window):
        self.focused = window

    def focus_first(self):
        try:
            return self.clients[0]
        except IndexError:
            pass

    def focus_last(self):
        try:
            return self.clients[-1]
        except IndexError:
            pass

    def focus_next(self, window):
        if not self.clients:
            return

        try:
            index = self.clients.index(window)
            return self.clients[index + 1]
        except IndexError:
            pass

    def focus_previous(self, window):
        if not self.clients:
            return

        try:
            index = self.clients.index(window)
            return self.clients[index - 1]
        except IndexError:
            pass

    def grow(self):
        if self.ratio + self.steps < 1:
            self.ratio += self.steps
            self.group.layoutAll()

    def shrink(self):
        if self.ratio - self.steps > 0:
            self.ratio -= self.steps
            self.group.layoutAll()

    def cmd_next(self):
        self.focus_next(self.focused)
        self.group.focus(self.focused)

    def cmd_previous(self):
        self.focus_previous(self.focused)
        self.group.focus(self.focused)

    def cmd_down(self):
        self.focus_next(self.focused)
        self.group.focus(self.focused)

    def cmd_up(self):
        self.focus_previous(self.focused)
        self.group.focus(self.focused)

    def cmd_shuffle_up(self):
        index = self.clients.index(self.focused)

        try:
            self.clients[index], self.clients[index - 1] =\
                self.clients[index - 1], self.clients[index]
        except IndexError:
            self.clients[index], self.clients[-1] =\
                self.clients[-1], self.clients[index]

        self.group.layoutAll()

    def cmd_shuffle_down(self):
        index = self.clients.index(self.focused)

        try:
            self.clients[index], self.clients[index + 1] =\
                self.clients[index + 1], self.clients[index]
        except IndexError:
            self.clients[index], self.clients[0] =\
                self.clients[0], self.clients[index]

        self.group.layoutAll()

    def cmd_maximize(self):
        if self.clients:
            self.maximized = self.focused
            self.group.layoutAll()

    def cmd_normalize(self):
        self.maximized = None
        self.group.layoutAll()

    def cmd_grow(self):
        if not self.maximized:
            return

        if self.focused is self.maximized:
            self.grow()
        else:
            self.shrink()

    def cmd_shrink(self):
        if not self.maximized:
            return

        if self.focused is self.maximized:
            self.shrink()
        else:
            self.grow()
