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

from libqtile.layout.base import _SimpleLayoutBase


class Tile(_SimpleLayoutBase):
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("name", "tile", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, ratio=0.618, masterWindows=1, expand=True,  # noqa: N803
                 ratio_increment=0.05, add_on_top=True, add_after_last=False,
                 shift_windows=False, master_match=None, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Tile.defaults)
        self.ratio = ratio
        self.master = masterWindows
        self.expand = expand
        self.ratio_increment = ratio_increment
        self.add_on_top = add_on_top
        self.add_after_last = add_after_last
        self.shift_windows = shift_windows
        self.master_match = master_match

    @property
    def master_windows(self):
        return self.clients[:self.master]

    @property
    def slave_windows(self):
        return self.clients[self.master:]

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
        if not match and self.master_match:
            match = self.master_match
        else:
            return
        if self.clients:
            masters = [c for c in self.clients if match.compare(c)]
            for client in reversed(masters):
                self.clients.remove(client)
                self.clients.append_head(client)

    def shift(self, idx1, idx2):
        if self.clients:
            self.clients[idx1], self.clients[idx2] = \
                self.clients[idx2], self.clients[idx1]
            self.group.layout_all(True)

    def clone(self, group):
        c = _SimpleLayoutBase.clone(self, group)
        return c

    def add(self, client, offset_to_current=0):
        if self.add_after_last:
            self.clients.append(client)
        elif self.add_on_top:
            self.clients.append_head(client)
        else:
            self.clients.add(client, offset_to_current)
        self.reset_master()

    def configure(self, client, screen):
        screen_width = screen.width
        screen_height = screen.height
        border_width = self.border_width
        if self.clients and client in self.clients:
            pos = self.clients.index(client)
            if client in self.master_windows:
                w = int(screen_width * self.ratio) \
                    if len(self.slave_windows) or not self.expand \
                    else screen_width
                h = screen_height // self.master
                x = screen.x
                y = screen.y + pos * h
            else:
                w = screen_width - int(screen_width * self.ratio)
                h = screen_height // (len(self.slave_windows))
                x = screen.x + int(screen_width * self.ratio)
                y = screen.y + self.clients[self.master:].index(client) * h
            if client.has_focus:
                bc = self.group.qtile.color_pixel(self.border_focus)
            else:
                bc = self.group.qtile.color_pixel(self.border_normal)
            client.place(
                x,
                y,
                w - border_width * 2,
                h - border_width * 2,
                border_width,
                bc,
                margin=self.margin,
            )
            client.unhide()
        else:
            client.hide()

    def info(self):
        d = _SimpleLayoutBase.info(self)
        d.update(dict(
            master=[c.name for c in self.master_windows],
            slave=[c.name for c in self.slave_windows],
        ))
        return d

    def cmd_shuffle_down(self):
        self.down()

    def cmd_shuffle_up(self):
        self.up()

    cmd_shuffle_left = cmd_shuffle_up
    cmd_shuffle_right = cmd_shuffle_down

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next
    cmd_up = cmd_previous
    cmd_down = cmd_next
    cmd_left = cmd_previous
    cmd_right = cmd_next

    def cmd_decrease_ratio(self):
        self.ratio -= self.ratio_increment
        self.group.layout_all()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layout_all()

    def cmd_decrease_nmaster(self):
        self.master -= 1
        if self.master <= 0:
            self.master = 1
        self.group.layout_all()

    def cmd_increase_nmaster(self):
        self.master += 1
        self.group.layout_all()
