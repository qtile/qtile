# -*- coding:utf-8 -*-
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012-2013, 2015 Tycho Andersen
# Copyright (c) 2013 Björn Lindström
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

import math

from .base import Layout
from .. import utils


ROWCOL = 1  # do rows at a time left to right top down
COLROW = 2  # do cols top to bottom, left to right

GOLDEN_RATIO = 1.618


class GridInfo(object):
    """
    Calculates sizes for grids
    >>> gi = GridInfo(.5, 5, 600, 480)
    >>> gi.calc()
    (1, 5, 1)
    >>> gi.get_sizes()
    [(0, 0, 120, 480), (120, 0, 120, 480), (240, 0, 120, 480), (360, 0, 120, 480), (480, 0, 120, 480)]
    >>> gi = GridInfo(6, 5, 600, 480)
    >>> gi.get_sizes()
    [(0, 0, 600, 96), (0, 96, 600, 96), (0, 192, 600, 96), (0, 288, 600, 96), (0, 384, 600, 96)]
    >>> gi = GridInfo(1, 5, 600, 480)
    >>> gi.get_sizes()
    [(0, 0, 200, 240), (200, 0, 200, 240), (400, 0, 200, 240), (0, 240, 300, 240), (200, 240, 200, 240)]

    >>> foo = GridInfo(1.6, 7, 400,370)
    >>> foo.get_sizes(500,580)


    """
    def __init__(self, ratio, num_windows, width, height):
        self.ratio = ratio
        self.num_windows = num_windows
        self.width = width
        self.height = height
        self.num_rows = 0
        self.num_cols = 0

    def calc(self, num_windows, width, height):
        """returns (rows, cols, orientation) tuple given input"""
        best_ratio = None
        best_rows_cols_orientation = None
        for rows, cols, orientation in self._possible_grids(num_windows):

            sample_width = width / cols
            sample_height = height / rows
            sample_ratio = sample_width / sample_height
            diff = abs(sample_ratio - self.ratio)
            if best_ratio is None or diff < best_ratio:
                best_ratio = diff
                best_rows_cols_orientation = (rows, cols, orientation)

        return best_rows_cols_orientation

    def _possible_grids(self, num_windows):
        """
        iterates over possible grids given a number of windows
        """
        if num_windows < 2:
            end = 2
        else:
            end = num_windows // 2 + 1
        for rows in range(1, end):
            cols = int(math.ceil(num_windows / rows))
            yield (rows, cols, ROWCOL)
            if rows != cols:
                # also want the reverse test
                yield (cols, rows, COLROW)

    def get_sizes_advanced(self, total_width, total_height,
                           xoffset=0, yoffset=0):
        """after every row/column recalculate remaining area"""
        results = []
        width = total_width
        height = total_height
        while len(results) < self.num_windows:
            remaining = self.num_windows - len(results)
            orien, sizes = self._get_row_or_col(
                remaining, width, height, xoffset, yoffset
            )
            results.extend(sizes)
            if orien == ROWCOL:
                # adjust height/yoffset
                height -= sizes[-1][-1]
                yoffset += sizes[-1][-1]
            else:
                width -= sizes[-1][-2]
                xoffset += sizes[-1][-2]

        return results

    def _get_row_or_col(self, num_windows, width, height, xoffset, yoffset):
        """process one row (or col) at a time"""
        rows, cols, orientation = self.calc(num_windows, width, height)
        results = []
        if orientation == ROWCOL:
            x = 0
            y = 0
            for i, col in enumerate(range(cols)):
                w_width = width // cols
                w_height = height // rows
                if i == cols - 1:
                    w_width = width - x
                results.append((x + xoffset, y + yoffset, w_width, w_height))
                x += w_width
        elif orientation == COLROW:
            x = 0
            y = 0
            for i, col in enumerate(range(rows)):
                w_width = width // cols
                w_height = height // rows
                if i == rows - 1:
                    w_height = height - y
                results.append((x + xoffset, y + yoffset, w_width, w_height))
                y += w_height
        return orientation, results

    def get_sizes(self, total_width, total_height, xoffset=0, yoffset=0):
        width = 0
        height = 0
        results = []
        rows, cols, orientation = self.calc(
            self.num_windows, total_width, total_height
        )
        if orientation == ROWCOL:
            y = 0
            for i, row in enumerate(range(rows)):
                x = 0
                width = total_width // cols
                for j, col in enumerate(range(cols)):
                    height = total_height // rows
                    if i == rows - 1 and j == 0:
                        # last row
                        remaining = self.num_windows - len(results)
                        width = total_width // remaining
                    elif j == cols - 1 or len(results) + 1 == self.num_windows:
                        # since we are dealing with integers,
                        # make last column (or item) take up remaining space
                        width = total_width - x

                    results.append((
                        x + xoffset,
                        y + yoffset,
                        width,
                        height
                    ))
                    if len(results) == self.num_windows:
                        return results
                    x += width
                y += height
        else:
            x = 0
            for i, col in enumerate(range(cols)):
                y = 0
                height = total_height // rows
                for j, row in enumerate(range(rows)):
                    width = total_width // cols
                    # down first
                    if i == cols - 1 and j == 0:
                        remaining = self.num_windows - len(results)
                        height = total_height // remaining
                    elif j == rows - 1 or len(results) + 1 == self.num_windows:
                        height = total_height - y
                    results.append((
                        x + xoffset,  # i * width + xoffset,
                        y + yoffset,  # j * height + yoffset,
                        width,
                        height
                    ))
                    if len(results) == self.num_windows:
                        return results
                    y += height
                x += width

        return results


class RatioTile(Layout):
    """Tries to tile all windows in the width/height ratio passed in"""
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("name", "ratiotile", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
        ("ratio", GOLDEN_RATIO, "Ratio of the tiles"),
        ("ratio_increment", 0.1, "Amount to increment per ratio increment"),
        ("fancy", False, "Use a different method to calculate window sizes."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(RatioTile.defaults)
        self.clients = []
        self.focused = None
        self.dirty = True  # need to recalculate
        self.layout_info = []
        self.last_size = None
        self.last_screen = None

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def focus(self, c):
        self.focused = c

    def blur(self):
        self.focused = None

    def add(self, w):
        self.dirty = True
        self.clients.insert(0, w)

    def remove(self, w):
        self.dirty = True
        if self.focused is w:
            self.focused = None
        self.clients.remove(w)
        if self.clients:  # and w is self.focused:
            self.focused = self.clients[0]
        return self.focused

    def configure(self, win, screen):
        # force recalc
        if not self.last_screen or self.last_screen != screen:
            self.last_screen = screen
            self.dirty = True
        if self.last_size and not self.dirty:
            if screen.width != self.last_size[0] or \
                    screen.height != self.last_size[1]:
                self.dirty = True
        if self.dirty:
            gi = GridInfo(
                self.ratio,
                len(self.clients),
                screen.width,
                screen.height
            )
            self.last_size = (screen.width, screen.height)
            if self.fancy:
                method = gi.get_sizes_advanced
            else:
                method = gi.get_sizes

            self.layout_info = method(
                screen.width,
                screen.height,
                screen.x,
                screen.y
            )

            self.dirty = False
        try:
            idx = self.clients.index(win)
        except ValueError:
            win.hide()
            return
        x, y, w, h = self.layout_info[idx]
        if win is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        win.place(
            x,
            y,
            w - self.border_width * 2,
            h - self.border_width * 2,
            self.border_width,
            bc,
            margin=self.margin,
        )
        win.unhide()

    def info(self):
        return {
            'clients': [x.name for x in self.clients],
            'ratio': self.ratio,
            'focused': self.focused.name if self.focused else None,
            'layout_info': self.layout_info
        }

    def shuffleUp(self):
        if self.clients:
            utils.shuffleUp(self.clients)
            self.group.layoutAll()

    def shuffleDown(self):
        if self.clients:
            utils.shuffleDown(self.clients)
            self.group.layoutAll()

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, win):
        idx = self.clients.index(win)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_previous(self, win):
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx - 1]

    def getNextClient(self):
        previndex = self.clients.index(self.focused) - 1
        if previndex < 0:
            previndex = len(self.clients) - 1
        return self.clients[previndex]

    def getPreviousClient(self):
        nextindex = self.clients.index(self.focused) + 1
        if nextindex >= len(self.clients):
            nextindex = 0
        return self.clients[nextindex]

    def next(self):
        n = self.getPreviousClient()
        self.group.focus(n)

    def previous(self):
        n = self.getNextClient()
        self.group.focus(n)

    def shuffle(self, function):
        if self.clients:
            function(self.clients)
            self.group.layoutAll()

    def cmd_down(self):
        self.previous()

    def cmd_up(self):
        self.next()

    def cmd_next(self):
        self.next()

    def cmd_previous(self):
        self.previous()

    def cmd_shuffle_down(self):
        self.shuffleDown()

    def cmd_shuffle_up(self):
        self.shuffleUp()

    def cmd_decrease_ratio(self):
        new_ratio = self.ratio - self.ratio_increment
        if new_ratio < 0:
            return
        self.ratio = new_ratio
        self.group.layoutAll()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layoutAll()

    def cmd_info(self):
        return self.info()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
