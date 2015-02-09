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
from .. import utils


class Tile(Layout):
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("name", "tile", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, ratio=0.618, masterWindows=1, expand=True,
                 ratio_increment=0.05, add_on_top=True, shift_windows=False,
                 master_match=None, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Tile.defaults)
        self.clients = []
        self.ratio = ratio
        self.master = masterWindows
        self.focused = None
        self.expand = expand
        self.ratio_increment = ratio_increment
        self.add_on_top = add_on_top
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
            self.shift_up()
        else:
            self.shuffle(utils.shuffleUp)

    def down(self):
        if self.shift_windows:
            self.shift_down()
        else:
            self.shuffle(utils.shuffleDown)

    def shift_up(self):
        if self.clients:
            currentindex = self.clients.index(self.focused)
            nextindex = (currentindex + 1) % len(self.clients)
            self.shift(currentindex, nextindex)

    def shift_down(self):
        if self.clients:
            currentindex = self.clients.index(self.focused)
            previndex = (currentindex - 1) % len(self.clients)
            self.shift(currentindex, previndex)

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_previous(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        if idx > 0:
            return self.clients[idx - 1]

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll(True)

    def resetMaster(self, match=None):
        if not match and self.master_match:
            match = self.master_match
        else:
            return
        if self.clients:
            masters = [c for c in self.clients if match.compare(c)]
            self.clients = masters + [
                c for c in self.clients if c not in masters
            ]

    def shift(self, idx1, idx2):
        if self.clients:
            self.clients[idx1], self.clients[idx2] = \
                self.clients[idx2], self.clients[idx1]
            self.group.layoutAll(True)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, client):
        self.focused = client

    def blur(self):
        self.focused = None

    def add(self, client):
        index = 0
        if not self.add_on_top and self.clients and self.focused:
            index = self.clients.index(self.focused)
        self.clients.insert(index, client)
        self.resetMaster()

    def remove(self, client):
        if client not in self.clients:
            return

        if self.focused is client:
            self.focused = None

        self.clients.remove(client)
        if self.clients and client is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, client, screen):
        screenWidth = screen.width
        screenHeight = screen.height
        x = 0
        y = 0
        w = 0
        h = 0
        borderWidth = self.border_width
        if self.clients and client in self.clients:
            pos = self.clients.index(client)
            if client in self.master_windows:
                w = int(screenWidth * self.ratio) \
                    if len(self.slave_windows) or not self.expand \
                    else screenWidth
                h = screenHeight // self.master
                x = screen.x
                y = screen.y + pos * h
            else:
                w = screenWidth - int(screenWidth * self.ratio)
                h = screenHeight // (len(self.slave_windows))
                x = screen.x + int(screenWidth * self.ratio)
                y = screen.y + self.clients[self.master:].index(client) * h
            if client is self.focused:
                bc = self.group.qtile.colorPixel(self.border_focus)
            else:
                bc = self.group.qtile.colorPixel(self.border_normal)
            client.place(
                x,
                y,
                w - borderWidth * 2,
                h - borderWidth * 2,
                borderWidth,
                bc,
                margin=self.margin,
            )
            client.unhide()
        else:
            client.hide()

    def info(self):
        return dict(
            clients=[c.name for c in self.clients],
            master=[c.name for c in self.master_windows],
            slave=[c.name for c in self.slave_windows],
        )

    def cmd_down(self):
        self.down()

    def cmd_up(self):
        self.up()

    def cmd_next(self):
        client = self.focus_next(self.focused) or self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or self.focus_last()
        self.group.focus(client, False)

    def cmd_decrease_ratio(self):
        self.ratio -= self.ratio_increment
        self.group.layoutAll()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layoutAll()

    def cmd_decrease_nmaster(self):
        self.master -= 1
        if self.master <= 0:
            self.master = 1
        self.group.layoutAll()

    def cmd_increase_nmaster(self):
        self.master += 1
        self.group.layoutAll()
