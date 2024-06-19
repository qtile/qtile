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
from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile.command.base import expose_command
from libqtile.layout.base import _SimpleLayoutBase

if TYPE_CHECKING:
    from typing import Self

    from libqtile.backend.base import Window
    from libqtile.group import _Group


class VerticalTile(_SimpleLayoutBase):
    """Tiling layout that works nice on vertically mounted monitors

    The available height gets divided by the number of panes, if no pane is
    maximized. If one pane has been maximized, the available height gets split
    in master and secondary area. The maximized pane (master pane) gets the
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

        Normal behavior.                 One maximized pane in the master area
        No maximized pane.               and two secondary panes in the
        No specific areas.               secondary area.

    ::

        -----------------------------------  In some cases, VerticalTile can be
        |                                 |  useful on horizontal mounted
        |                1                |  monitors too.
        |                                 |  For example, if you want to have a
        |---------------------------------|  web browser and a shell below it.
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
        ("border_focus", "#FF0000", "Border color(s) for the focused window."),
        ("border_normal", "#FFFFFF", "Border color(s) for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("single_border_width", None, "Border width for single window."),
        ("single_margin", None, "Margin for single window."),
        ("margin", 0, "Border margin (int or list of ints [N E S W])."),
    ]

    ratio = 0.75
    steps = 0.05

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(VerticalTile.defaults)
        if self.single_border_width is None:
            self.single_border_width = self.border_width
        if self.single_margin is None:
            self.single_margin = self.margin
        self.maximized = None

    def add_client(self, window):
        return self.clients.add_client(window, 1)

    def remove(self, window: Window) -> Window | None:
        if self.maximized is window:
            self.maximized = None
        return self.clients.remove(window)

    def clone(self, group: _Group) -> Self:
        c = _SimpleLayoutBase.clone(self, group)
        c.maximized = None
        return c

    def configure(self, window, screen_rect):
        if self.clients and window in self.clients:
            n = len(self.clients)
            index = self.clients.index(window)

            # border
            border_width = self.border_width if n > 1 else self.single_border_width
            border_color = self.border_focus if window.has_focus else self.border_normal

            # margin
            margin = self.margin if n > 1 else self.single_margin

            # width
            width = screen_rect.width - border_width * 2

            # y
            y = screen_rect.y

            # height
            if n > 1:
                main_area_height = int(screen_rect.height * self.ratio)
                sec_area_height = screen_rect.height - main_area_height

                main_pane_height = main_area_height - border_width * 2
                sec_pane_height = sec_area_height // (n - 1) - border_width * 2
                normal_pane_height = (screen_rect.height // n) - (border_width * 2)

                if self.maximized:
                    y += (index * sec_pane_height) + (border_width * 2 * index)
                    if window is self.maximized:
                        height = main_pane_height
                    else:
                        height = sec_pane_height
                        if index > self.clients.index(self.maximized):
                            y = y - sec_pane_height + main_pane_height
                else:
                    height = normal_pane_height
                    y += (index * normal_pane_height) + (border_width * 2 * index)
            else:
                height = screen_rect.height - 2 * border_width

            window.place(
                screen_rect.x, y, width, height, border_width, border_color, margin=margin
            )
            window.unhide()
        else:
            window.hide()

    def _grow(self):
        if self.ratio + self.steps < 1:
            self.ratio += self.steps
            self.group.layout_all()

    def _shrink(self):
        if self.ratio - self.steps > 0:
            self.ratio -= self.steps
            self.group.layout_all()

    @expose_command("up")
    def previous(self) -> None:
        _SimpleLayoutBase.previous(self)

    @expose_command("down")
    def next(self) -> None:
        _SimpleLayoutBase.next(self)

    @expose_command()
    def shuffle_up(self):
        self.clients.shuffle_up()
        self.group.layout_all()

    @expose_command()
    def shuffle_down(self):
        self.clients.shuffle_down()
        self.group.layout_all()

    @expose_command()
    def maximize(self):
        if self.clients:
            self.maximized = self.clients.current_client
            self.group.layout_all()

    @expose_command()
    def normalize(self):
        self.maximized = None
        self.group.layout_all()

    @expose_command()
    def grow(self):
        if not self.maximized:
            return
        if self.clients.current_client is self.maximized:
            self._grow()
        else:
            self._shrink()

    @expose_command()
    def shrink(self):
        if not self.maximized:
            return
        if self.clients.current_client is self.maximized:
            self._shrink()
        else:
            self._grow()
