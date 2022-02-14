# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Tycho Andersen
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
from __future__ import annotations

import math

from libqtile.layout.base import _SimpleLayoutBase
from libqtile.log_utils import logger


class Matrix(_SimpleLayoutBase):
    """
    This layout divides the screen into a matrix of equally sized cells and
    places one window in each cell. The number of columns is configurable and
    can also be changed interactively.
    """

    defaults = [
        ("border_focus", "#0000ff", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("columns", 2, "Number of columns"),
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])"),
    ]

    def __init__(self, _columns: int | None = None, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Matrix.defaults)
        if _columns:
            logger.warning(
                "The use of a positional argument in Matrix is deprecated. "
                "Please update your config to use columns=..."
            )
            self.columns = _columns

    @property
    def rows(self):
        """Calc current number of rows, basd on number of clients and columns"""
        return int(math.ceil(len(self.clients) / self.columns))

    @property
    def row(self):
        """Calc row index of current client"""
        return self.clients.current_index // self.columns

    @property
    def column(self):
        """Calc column index of current client"""
        return self.clients.current_index % self.columns

    def info(self):
        d = _SimpleLayoutBase.info(self)
        d["rows"] = [[win.name for win in self.get_row(i)] for i in range(self.rows)]
        d["current_window"] = self.column, self.row
        return d

    def clone(self, group):
        c = _SimpleLayoutBase.clone(self, group)
        c.columns = self.columns
        return c

    def get_row(self, row):
        """Get all clients in given row"""
        assert row < self.rows
        return self.clients[row * self.columns : row * self.columns + self.columns]

    def get_column(self, column):
        """Get all clients in given column"""
        assert column < self.columns
        return [self.clients[i] for i in range(column, len(self.clients), self.columns)]

    def add(self, client):
        """Add client to Layout.
        Note that for Matrix the clients are appended at end of list.
        If needed a new row in matrix is created"""
        return self.clients.append(client)

    def configure(self, client, screen_rect):
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        row = idx // self.columns
        col = idx % self.columns
        column_size = int(math.ceil(len(self.clients) / self.columns))
        if client.has_focus:
            px = self.border_focus
        else:
            px = self.border_normal
        # calculate position and size
        column_width = int(screen_rect.width / float(self.columns))
        row_height = int(screen_rect.height / float(column_size))
        xoffset = screen_rect.x + col * column_width
        yoffset = screen_rect.y + row * row_height
        win_width = column_width - 2 * self.border_width
        win_height = row_height - 2 * self.border_width
        # place
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

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next

    def horizontal_traversal(self, direction):
        """
        Internal method for determining left or right client.
        Negative direction is to left
        """
        column, row = self.column, self.row
        column = (column + direction) % len(self.get_row(row))
        self.clients.current_index = row * self.columns + column
        self.group.focus(self.clients.current_client)

    def vertical_traversal(self, direction):
        """
        internal method for determining above or below client.
        Negative direction is to top
        """
        column, row = self.column, self.row
        row = (row + direction) % len(self.get_column(column))
        self.clients.current_index = row * self.columns + column
        self.group.focus(self.clients.current_client)

    def cmd_left(self):
        """Switch to the next window on current row"""
        self.horizontal_traversal(-1)

    def cmd_right(self):
        """Switch to the next window on current row"""
        self.horizontal_traversal(+1)

    def cmd_up(self):
        """Switch to the previous window in current column"""
        self.vertical_traversal(-1)

    def cmd_down(self):
        """Switch to the next window in current column"""
        self.vertical_traversal(+1)

    def cmd_delete(self):
        """Decrease number of columns"""
        self.columns -= 1
        self.group.layout_all()

    def cmd_add(self):
        """Increase number of columns"""
        self.columns += 1
        self.group.layout_all()
