# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2017 Dirk Hartmann
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


class Zoomy(_SimpleLayoutBase):
    """A layout with single active windows, and few other previews at the right"""
    defaults = [
        ("columnwidth", 150, "Width of the right column"),
        ("property_name", "ZOOM", "Property to set on zoomed window"),
        ("property_small", "0.1", "Property value to set on zoomed window"),
        ("property_big", "1.0", "Property value to set on normal window"),
        ("margin", 0, "Margin of the layout"),
        ("name", "zoomy", "Name of this layout."),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Zoomy.defaults)

    def add(self, client):
        self.clients.append_head(client)

    def configure(self, client, screen):
        left, right = screen.hsplit(screen.width - self.columnwidth)
        if client is self.clients.current_client:
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
            focused_index = self.clients.current_index
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

    def focus(self, win):
        if (self.clients.current_client and
            self.property_name and
            self.clients.current_client.window.get_property(
                self.property_name, "UTF8_STRING") is not None):

            self.clients.current_client.window.set_property(
                self.property_name,
                self.property_small,
                "UTF8_STRING", format=8)
        _SimpleLayoutBase.focus(self, win)
        if self.property_name:
            win.window.set_property(self.property_name,
                                    self.property_big,
                                    "UTF8_STRING", format=8)

    cmd_next = _SimpleLayoutBase.next
    cmd_down = _SimpleLayoutBase.next

    cmd_previous = _SimpleLayoutBase.previous
    cmd_up = _SimpleLayoutBase.previous
