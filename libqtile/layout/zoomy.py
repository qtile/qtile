# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012, 2014 Tycho Andersen
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

from .base import SingleWindow


class Zoomy(SingleWindow):
    """
        A layout with single active windows, and few other previews at the
        right
    """
    defaults = [
        ("columnwidth", 150, "Width of the right column"),
        ("property_name", "ZOOM", "Property to set on zoomed window"),
        ("property_small", "0.1", "Property value to set on zoomed window"),
        ("property_big", "1.0", "Property value to set on normal window"),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, **config):
        SingleWindow.__init__(self, **config)
        self.add_defaults(Zoomy.defaults)
        self.clients = []
        self.focused = None

    def _get_window(self):
        return self.focused

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_next(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        return self.clients[(idx + 1) % len(self.clients)]

    def focus_previous(self, client):
        if not self.clients:
            return
        idx = self.clients.index(client)
        return self.clients[idx - 1]

    def clone(self, group):
        c = SingleWindow.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        self.clients.insert(0, client)
        self.focus(client)

    def remove(self, client):
        if client not in self.clients:
            return
        if self.focused == client:
            self.focused = self.focus_previous(client)
        if self.focused == client:
            self.focused = None
        self.clients.remove(client)
        return self.focused

    def configure(self, client, screen):
        left, right = screen.hsplit(screen.width - self.columnwidth)
        if client is self.focused:
            client.place(
                left.x,
                left.y,
                left.width,
                left.height,
                0,
                None,
                margin=self.margin,
            )
        else:
            h = right.width * left.height // left.width
            client_index = self.clients.index(client)
            focused_index = self.clients.index(self.focused)
            offset = client_index - focused_index - 1
            if offset < 0:
                offset += len(self.clients)
            if h * (len(self.clients) - 1) < right.height:
                client.place(
                    right.x,
                    right.y + h * offset,
                    right.width,
                    h,
                    0,
                    None,
                    margin=self.margin,
                )
            else:
                hh = (right.height - h) // (len(self.clients) - 1)
                client.place(
                    right.x,
                    right.y + hh * offset,
                    right.width,
                    h,
                    0,
                    None,
                    margin=self.margin,
                )
        client.unhide()

    def info(self):
        d = SingleWindow.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def focus(self, win):
        if self.focused and self.property_name and self.focused.window.get_property(
            self.property_name,
            "UTF8_STRING"
        ) is not None:
            self.focused.window.set_property(
                self.property_name,
                self.property_small,
                "UTF8_STRING",
                format=8
            )
        SingleWindow.focus(self, win)
        if self.property_name:
            self.focused = win
            win.window.set_property(
                self.property_name,
                self.property_big,
                "UTF8_STRING",
                format=8
            )

    def cmd_next(self):
        client = self.focus_next(self.focused) or self.focus_first()
        self.group.focus(client, False)

    cmd_down = cmd_next

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or self.focus_last()
        self.group.focus(client, False)

    cmd_up = cmd_previous
