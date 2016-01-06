# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Tycho Andersen
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

import math

from .base import Layout


class Matrix(Layout):
    """
        This layout divides the screen into a matrix of equally sized cells
        and places one window in each cell. The number of columns is
        configurable and can also be changed interactively.
    """
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("name", "matrix", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, columns=2, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Matrix.defaults)
        self.current_window = None
        self.columns = columns
        self.clients = []

    def info(self):
        d = Layout.info(self)
        d["rows"] = [
            [win.name for win in self.get_row(i)]
            for i in range(self.get_num_rows())
        ]
        d["current_window"] = self.current_window
        d["clients"] = [x.name for x in self.clients]
        return d

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def get_current_window(self):
        c, r = self.current_window
        return self.clients[r * self.columns + c]

    def get_num_rows(self):
        return int(math.ceil(len(self.clients) / self.columns))

    def get_row(self, row):
        assert row < self.get_num_rows()
        return self.clients[
            row * self.columns: row * self.columns + self.columns
        ]

    def get_column(self, column):
        assert column < self.columns
        return [
            self.clients[i]
            for i in range(column, len(self.clients), self.columns)
        ]

    def add(self, client):
        self.clients.append(client)

    def remove(self, client):
        if client not in self.clients:
            return
        self.clients.remove(client)

    def focus(self, client):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        self.current_window = (idx % self.columns, idx // self.columns)

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_next(self, window):
        if not self.clients:
            return
        if self.get_current_window != window:
            self.focus(window)
        idx = self.clients.index(window)
        if idx + 1 < len(self.clients):
            return self.clients[idx + 1]

    def focus_previous(self, window):
        if not self.clients:
            return
        if self.get_current_window != window:
            self.focus(window)
        idx = self.clients.index(window)
        if idx > 0:
            return self.clients[idx - 1]

    def configure(self, client, screen):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        column = idx % self.columns
        row = idx // self.columns
        column_size = int(math.ceil(len(self.clients) / self.columns))
        if (column, row) == self.current_window:
            px = self.group.qtile.colorPixel(self.border_focus)
        else:
            px = self.group.qtile.colorPixel(self.border_normal)
        column_width = int(screen.width / float(self.columns))
        row_height = int(screen.height / float(column_size))
        xoffset = screen.x + column * column_width
        yoffset = screen.y + row * row_height
        win_width = column_width - 2 * self.border_width
        win_height = row_height - 2 * self.border_width

        client.place(
            xoffset,
            yoffset,
            win_width,
            win_height,
            self.border_width,
            px,
            margin=self.margin,
        )
        client.unhide()

    def cmd_next(self):
        client = self.focus_next(self.get_current_window()) or \
            self.focus_first()
        self.group.focus(client)

    def cmd_previous(self):
        client = self.focus_previous(self.get_current_window()) or \
            self.focus_last()
        self.group.focus(client)

    def cmd_left(self):
        """
            Switch to the next window on current row
        """
        column, row = self.current_window
        self.current_window = ((column - 1) % len(self.get_row(row)), row)
        self.group.focus(self.get_current_window())

    def cmd_right(self):
        """
            Switch to the next window on current row
        """
        column, row = self.current_window
        self.current_window = ((column + 1) % len(self.get_row(row)), row)
        self.group.focus(self.get_current_window())

    def cmd_down(self):
        """
            Switch to the next window in current column
        """
        column, row = self.current_window
        self.current_window = (
            column,
            (row + 1) % len(self.get_column(column))
        )
        self.group.focus(self.get_current_window())

    def cmd_up(self):
        """
            Switch to the previous window in current column
        """
        column, row = self.current_window
        self.current_window = (
            column,
            (row - 1) % len(self.get_column(column))
        )
        self.group.focus(self.get_current_window())

    def cmd_delete(self):
        """
            Decrease number of columns
        """
        self.columns -= 1
        self.group.layoutAll()

    def cmd_add(self):
        """
            Increase number of columns
        """
        self.columns += 1
        self.group.layoutAll()
