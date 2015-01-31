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

from .base import Layout


class VerticalTile(Layout):
    """
    VerticalTile implements a tiling layout that works nice on vertically
    mounted monitors.
    The available height gets divided by the number of panes, if no pane
    is maximized. If one pane has been maximized, the available height gets
    split in master- and secondary area. The maximized pane (master pane)
    gets the full height of the master area and the other panes
    (secondary panes) share the remaining space.
    The master area (at default 75%) can grow and shrink via keybindings.

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
        ('border_normal', '#FFFFFF', 'Border color for un-focused winows.'),
        ('border_width', 1, 'Border width.'),
        ('margin', 0, 'Border margin.'),
        ('name', 'VerticalTile', 'Name of this layout.'),
    ]

    windows = []
    focused = None
    maximized = None
    ratio = 0.75
    steps = 0.05

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(self.defaults)

    def add(self, window):
        if self.windows and self.focused:
            index = self.windows.index(self.focused)
            self.windows.insert(index + 1, window)
        else:
            self.windows.append(window)

        self.focus(window)

    def remove(self, window):
        if window not in self.windows:
            return

        index = self.windows.index(window)
        self.windows.remove(window)

        if not self.windows:
            self.focused = None
            self.maximized = None
            return

        if self.maximized is window:
            self.maximized = None

        if index == len(self.windows):
            index -= 1

        self.focus(self.windows[index])
        return self.focused

    def clone(self, group):
        c = Layout.clone(self, group)
        c.windows = []
        c.focused = None
        return c

    def configure(self, window, screen):
        if self.windows and window in self.windows:
            n = len(self.windows)
            index = self.windows.index(window)

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
                sec_pane_height = sec_area_height / (n - 1) - border_width * 2
                normal_pane_height = (screen.height / n) - (border_width * 2)

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
                    if index > self.windows.index(self.maximized):
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
            self.focus(self.windows[0])
        except IndexError:
            self.blur()

    def focus_last(self):
        try:
            self.focus(self.windows[-1])
        except IndexError:
            self.blur()

    def focus_next(self):
        try:
            index = self.windows.index(self.focused)
            self.focus(self.windows[index + 1])
        except IndexError:
            self.focus_first()

    def focus_previous(self):
        try:
            index = self.windows.index(self.focused)
            self.focus(self.windows[index - 1])
        except IndexError:
            self.focus_last()

    def grow(self):
        if self.ratio + self.steps < 1:
            self.ratio += self.steps
            self.group.layoutAll()

    def shrink(self):
        if self.ratio - self.steps > 0:
            self.ratio -= self.steps
            self.group.layoutAll()

    def cmd_next(self):
        self.focus_next()
        self.group.focus(self.focused, False)

    def cmd_previous(self):
        self.focus_previous()
        self.group.focus(self.focused, False)

    def cmd_down(self):
        self.focus_next()
        self.group.focus(self.focused, False)

    def cmd_up(self):
        self.focus_previous()
        self.group.focus(self.focused, False)

    def cmd_shuffle_up(self):
        index = self.windows.index(self.focused)

        try:
            self.windows[index], self.windows[index - 1] =\
                self.windows[index - 1], self.windows[index]
        except IndexError:
            self.windows[index], self.windows[-1] =\
                self.windows[-1], self.windows[index]

        self.group.layoutAll()

    def cmd_shuffle_down(self):
        index = self.windows.index(self.focused)

        try:
            self.windows[index], self.windows[index + 1] =\
                self.windows[index + 1], self.windows[index]
        except IndexError:
            self.windows[index], self.windows[0] =\
                self.windows[0], self.windows[index]

        self.group.layoutAll()

    def cmd_maximize(self):
        if self.windows:
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
