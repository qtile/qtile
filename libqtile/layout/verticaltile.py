# Copyright (c) 2014, Florian Scherf <fscherf@gmx.net>. All rights reserved.
# Copyright (c) 2017, Dirk Hartmann.
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

from .base import _SimpleLayoutBase


class VerticalTile(_SimpleLayoutBase):
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
        ('name', 'verticaltile', 'Name of this layout.'),
    ]

    ratio = 0.75
    steps = 0.05

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(VerticalTile.defaults)
        self.maximized = None

    def add(self, window):
        return self.clients.add(window, 1)

    def remove(self, window):
        if self.maximized is window:
            self.maximized = None
        return self.clients.remove(window)

    def clone(self, group):
        c = _SimpleLayoutBase.clone(self, group)
        c.maximized = None
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

            if window.has_focus:
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

    def grow(self):
        if self.ratio + self.steps < 1:
            self.ratio += self.steps
            self.group.layoutAll()

    def shrink(self):
        if self.ratio - self.steps > 0:
            self.ratio -= self.steps
            self.group.layoutAll()

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next

    cmd_up = cmd_previous
    cmd_down = cmd_next

    def cmd_shuffle_up(self):
        self.clients.shuffle_up()
        self.group.layoutAll()

    def cmd_shuffle_down(self):
        self.clients.shuffle_down()
        self.group.layoutAll()

    def cmd_maximize(self):
        if self.clients:
            self.maximized = self.clients.current_client
            self.group.layoutAll()

    def cmd_normalize(self):
        self.maximized = None
        self.group.layoutAll()

    def cmd_grow(self):
        if not self.maximized:
            return
        if self.clients.current_client is self.maximized:
            self.grow()
        else:
            self.shrink()

    def cmd_shrink(self):
        if not self.maximized:
            return
        if self.clients.current_client is self.maximized:
            self.shrink()
        else:
            self.grow()
