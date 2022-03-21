# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2010-2011 Paul Colomiets
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Tzbob
# Copyright (c) 2012 roger
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2017 Dirk Hartmann.
# Copyright (c) 2018 Nazar Mokrynskyi
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

from libqtile.config import Match
from libqtile.layout.base import _SimpleLayoutBase


class Tile(_SimpleLayoutBase):
    """A layout with two stacks of windows dividing the screen

    The Tile layout divides the screen_rect horizontally into two stacks. The
    maximum amount of "master" windows can be configured; surplus windows will
    be displayed in the slave stack on the right.
    Within their stacks, the windows will be tiled vertically.
    The windows can be rotated in their entirety by calling up() or down() or,
    if shift_windows is set to True, individually.
    """

    defaults = [
        ("border_focus", "#0000ff", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        ("border_on_single", True, "Whether to draw border if there is only one window."),
        ("border_width", 1, "Border width."),
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])"),
        ("margin_on_single", True, "Whether to draw margin if there is only one window."),
        ("ratio", 0.618, "Width-percentage of screen size reserved for master windows."),
        ("max_ratio", 0.85, "Maximum width of master windows"),
        ("min_ratio", 0.15, "Minimum width of master windows"),
        (
            "master_length",
            1,
            "Amount of windows displayed in the master stack. Surplus windows "
            "will be moved to the slave stack.",
        ),
        (
            "expand",
            True,
            "Expand the master windows to the full screen width if no slaves " "are present.",
        ),
        (
            "ratio_increment",
            0.05,
            "By which amount to change ratio when cmd_decrease_ratio or "
            "cmd_increase_ratio are called.",
        ),
        (
            "add_on_top",
            True,
            "Add new clients before all the others, potentially pushing other "
            "windows into slave stack.",
        ),
        (
            "add_after_last",
            False,
            "Add new clients after all the others. If this is True, it " "overrides add_on_top.",
        ),
        (
            "shift_windows",
            False,
            "Allow to shift windows within the layout. If False, the layout "
            "will be rotated instead.",
        ),
        (
            "master_match",
            None,
            "A Match object defining which window(s) should be kept masters (single or a list "
            "of Match-objects).",
        ),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Tile.defaults)
        self._initial_ratio = self.ratio

    @property
    def ratio_size(self):
        return self.ratio

    @ratio_size.setter
    def ratio_size(self, ratio):
        self.ratio = min(max(ratio, self.min_ratio), self.max_ratio)

    @property
    def master_windows(self):
        return self.clients[: self.master_length]

    @property
    def slave_windows(self):
        return self.clients[self.master_length :]

    def up(self):
        if self.shift_windows:
            self.clients.shuffle_up()
        else:
            self.clients.rotate_down()
        self.group.layout_all()

    def down(self):
        if self.shift_windows:
            self.clients.shuffle_down()
        else:
            self.clients.rotate_up()
        self.group.layout_all()

    def reset_master(self, match=None):
        if not match and not self.master_match:
            return
        if self.clients:
            master_match = match or self.master_match
            if isinstance(master_match, Match):
                master_match = [master_match]
            masters = []
            for c in self.clients:
                for match in master_match:
                    if match.compare(c):
                        masters.append(c)
            for client in reversed(masters):
                self.clients.remove(client)
                self.clients.append_head(client)

    def clone(self, group):
        c = _SimpleLayoutBase.clone(self, group)
        return c

    def add(self, client, offset_to_current=1):
        if self.add_after_last:
            self.clients.append(client)
        elif self.add_on_top:
            self.clients.append_head(client)
        else:
            super().add(client, offset_to_current)
        self.reset_master()

    def configure(self, client, screen_rect):
        screen_width = screen_rect.width
        screen_height = screen_rect.height
        border_width = self.border_width
        if self.clients and client in self.clients:
            pos = self.clients.index(client)
            if client in self.master_windows:
                w = (
                    int(screen_width * self.ratio_size)
                    if len(self.slave_windows) or not self.expand
                    else screen_width
                )
                h = screen_height // self.master_length
                x = screen_rect.x
                y = screen_rect.y + pos * h
            else:
                w = screen_width - int(screen_width * self.ratio_size)
                h = screen_height // (len(self.slave_windows))
                x = screen_rect.x + int(screen_width * self.ratio_size)
                y = screen_rect.y + self.clients[self.master_length :].index(client) * h
            if client.has_focus:
                bc = self.border_focus
            else:
                bc = self.border_normal
            if not self.border_on_single and len(self.clients) == 1:
                border_width = 0
            else:
                border_width = self.border_width
            client.place(
                x,
                y,
                w - border_width * 2,
                h - border_width * 2,
                border_width,
                bc,
                margin=0
                if (not self.margin_on_single and len(self.clients) == 1)
                else self.margin,
            )
            client.unhide()
        else:
            client.hide()

    def info(self):
        d = _SimpleLayoutBase.info(self)
        d.update(
            dict(
                master=[c.name for c in self.master_windows],
                slave=[c.name for c in self.slave_windows],
            )
        )
        return d

    def cmd_shuffle_down(self):
        self.down()

    def cmd_shuffle_up(self):
        self.up()

    def cmd_reset(self):
        self.ratio_size = self._initial_ratio
        self.group.layout_all()

    cmd_normalize = cmd_reset

    cmd_shuffle_left = cmd_shuffle_up
    cmd_shuffle_right = cmd_shuffle_down

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next
    cmd_up = cmd_previous
    cmd_down = cmd_next
    cmd_left = cmd_previous
    cmd_right = cmd_next

    def cmd_decrease_ratio(self):
        self.ratio_size -= self.ratio_increment
        self.group.layout_all()

    def cmd_increase_ratio(self):
        self.ratio_size += self.ratio_increment
        self.group.layout_all()

    def cmd_decrease_nmaster(self):
        self.master_length -= 1
        if self.master_length <= 0:
            self.master_length = 1
        self.group.layout_all()

    def cmd_increase_nmaster(self):
        self.master_length += 1
        self.group.layout_all()
