# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2015 Serge Hallyn
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

# We have an array of columns.  Each columns is a dict containing
# width (in percent), rows (an array of rows), and mode, which is
# either 'stack' or 'split'
#
# Each row is an array of clients

class Wmii(Layout):
    """This layout emulates wmii layouts

    The screen it split into columns, always starting with one.  A new window
    is created in the active window's column.  Windows can be shifted left and
    right.  If there is no column when shifting, a new one is created.  Each
    column can be stacked or divided (equally split).

    This layout implements something akin to wmii's semantics.

    Each group starts with one column.  The first window takes up the whole
    screen.  Next window splits the column in half.  Windows can be moved to
    the column to the left or right.  If there is no column in the direction
    being moved into, a new column is created.

    Each column can be either stacked (each window takes up the whole vertical
    real estate) or split (the windows are split equally vertically in the
    column) Columns can be grown horizontally (cmd_grow_left/right).

    My config.py has the following added::

        Key(
            [mod, "shift", "control"], "l",
            lazy.layout.grow_right()
        ),
        Key(
            [mod, "shift"], "l",
            lazy.layout.shuffle_right()
        ),
        Key(
            [mod, "shift", "control"], "h",
            lazy.layout.grow_left()
        ),
        Key(
            [mod, "shift"], "h",
            lazy.layout.shuffle_left()
        ),
        Key(
            [mod], "s",
            lazy.layout.toggle_split()
        ),
    """
    defaults = [
        ("border_focus", "#881111", "Border colour for the focused window."),
        ("border_normal", "#220000", "Border colour for un-focused windows."),
        ("border_focus_stack", "#0000ff", "Border colour for un-focused windows."),
        ("border_normal_stack", "#000022", "Border colour for un-focused windows."),
        ("grow_amount", 5, "Amount by which to grow/shrink a window."),
        ("border_width", 2, "Border width."),
        ("name", "wmii", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Wmii.defaults)
        self.current_window = None
        self.clients = []
        self.columns = [{'active': 0, 'width': 100, 'mode': 'split', 'rows': []}]

    def info(self):
        d = Layout.info(self)
        d["current_window"] = self.current_window.name if self.current_window else None
        d["clients"] = [x.name for x in self.clients]
        return d

    def add_column(self, prepend, win):
        newwidth = int(100 / (len(self.columns) + 1))
        # we are only called if there already is a column, simplifies things
        for c in self.columns:
            c['width'] = newwidth
        c = {'width': newwidth, 'mode': 'split', 'rows': [win]}
        if prepend:
            self.columns.insert(0, c)
        else:
            self.columns.append(c)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.current_window = None
        c.clients = []
        c.columns = [{'active': 0, 'width': 100, 'mode': 'split', 'rows': []}]
        return c

    def current_column(self):
        if self.current_window is None:
            return None
        for c in self.columns:
            if self.current_window in c['rows']:
                return c
        return None

    def add(self, client):
        self.clients.append(client)
        c = self.current_column()
        if c is None:
            if len(self.columns) == 0:
                self.columns = [{'active': 0, 'width': 100, 'mode': 'split', 'rows': []}]
            c = self.columns[0]
        c['rows'].append(client)
        self.focus(client)

    def remove(self, client):
        if client not in self.clients:
            return
        self.clients.remove(client)
        for c in self.columns:
            if client in c['rows']:
                ridx = c['rows'].index(client)
                cidx = self.columns.index(c)
                c['rows'].remove(client)
                if len(c['rows']) != 0:
                    if client == self.current_window:
                        if ridx > 0:
                            ridx -= 1
                        return c['rows'][ridx]
                    return self.current_window
                # column is now empty, remove it and select the previous one
                self.columns.remove(c)
                if len(self.columns) == 0:
                    return None
                newwidth = int(100 / len(self.columns))
                for c in self.columns:
                    c['width'] = newwidth
                if len(self.columns) == 1:
                    # there is no window at all
                    return None
                if cidx > 0:
                    cidx -= 1
                c = self.columns[cidx]
                rows = c['rows']
                return rows[0]

    def is_last_column(self, cidx):
            return cidx == len(self.columns) - 1

    def focus(self, client):
        self.current_window = client
        for c in self.columns:
            if client in c['rows']:
                c['active'] = c['rows'].index(client)

    def configure(self, client, screen):
        show = True
        if client not in self.clients:
            return
        ridx = -1
        xoffset = int(screen.x)
        for c in self.columns:
            if client in c['rows']:
                ridx = c['rows'].index(client)
                break
            xoffset += int(float(c['width']) * screen.width / 100.0)
        if ridx == -1:
            return
        if client == self.current_window:
            if c['mode'] == 'split':
                px = self.group.qtile.colorPixel(self.border_focus)
            else:
                px = self.group.qtile.colorPixel(self.border_focus_stack)
        else:
            if c['mode'] == 'split':
                px = self.group.qtile.colorPixel(self.border_normal)
            else:
                px = self.group.qtile.colorPixel(self.border_normal_stack)
        if c['mode'] == 'split':
            oneheight = screen.height / len(c['rows'])
            yoffset = int(screen.y + oneheight * ridx)
            win_height = int(oneheight - 2 * self.border_width)
        else:  # stacked
            if c['active'] != c['rows'].index(client):
                show = False
            yoffset = int(screen.y)
            win_height = int(screen.height - 2 * self.border_width)
        win_width = int(float(c['width'] * screen.width / 100.0))
        win_width -= 2 * self.border_width

        if show:
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
        else:
            client.hide()

    def cmd_toggle_split(self):
        c = self.current_column()
        if c['mode'] == "split":
            c['mode'] = "stack"
        else:
            c['mode'] = "split"
        self.group.layoutAll()

    def focus_next(self, win):
        # First: try to get next window in column of win
        for idx, col in enumerate(self.columns):
            rows = col['rows']
            if win in rows:
                i = rows.index(win)
                if i + 1 < len(rows):
                    return rows[i + 1]
                else:
                    break
        # if there was no next, get first client from next column
        if idx + 1 < len(self.columns):
            rows = self.columns[idx + 1]['rows']
            if len(rows):
                return rows[0]

    def focus_previous(self, win):
        # First: try to focus previous client in column
        for idx, col in enumerate(self.columns):
            rows = col['rows']
            if win in rows:
                i = rows.index(win)
                if i > 0:
                    return rows[i - 1]
                else:
                    break
        # If there was no previous, get last from previous column
        if idx > 0:
            rows = self.columns[idx + 1]['rows']
            if len(rows):
                return rows[-1]

    def focus_first(self):
        if len(self.columns) == 0:
            self.columns = [{'active': 0, 'width': 100, 'mode': 'split', 'rows': []}]
        c = self.columns[0]
        if len(c['rows']) != 0:
            return c['rows'][0]

    def focus_last(self):
        c = self.columns[len(self.columns) - 1]
        if len(c['rows']) != 0:
            return c['rows'][len(c['rows']) - 1]

    def cmd_left(self):
        """Switch to the first window on prev column"""
        c = self.current_column()
        cidx = self.columns.index(c)
        if cidx == 0:
            return
        cidx -= 1
        c = self.columns[cidx]
        if c['mode'] == "split":
            self.group.focus(c['rows'][0])
        else:
            self.group.focus(c['rows'][c['active']])

    def cmd_right(self):
        """Switch to the first window on next column"""
        c = self.current_column()
        cidx = self.columns.index(c)
        if self.is_last_column(cidx):
            return
        cidx += 1
        c = self.columns[cidx]
        if c['mode'] == "split":
            self.group.focus(c['rows'][0])
        else:
            self.group.focus(c['rows'][c['active']])

    def cmd_up(self):
        """Switch to the previous window in current column"""
        c = self.current_column()
        if c is None:
            return
        ridx = c['rows'].index(self.current_window)
        if ridx == 0:
            if c['mode'] != "split":
                ridx = len(c['rows']) - 1
        else:
            ridx -= 1
        client = c['rows'][ridx]
        self.group.focus(client)

    def cmd_down(self):
        """Switch to the next window in current column"""
        c = self.current_column()
        if c is None:
            return
        ridx = c['rows'].index(self.current_window)
        if ridx == len(c['rows']) - 1:
            if c['mode'] != "split":
                ridx = 0
        else:
            ridx += 1
        client = c['rows'][ridx]
        self.group.focus(client)

    cmd_next = cmd_down
    cmd_previous = cmd_up

    def cmd_shuffle_left(self):
        cur = self.current_window
        if cur is None:
            return
        for c in self.columns:
            if cur in c['rows']:
                cidx = self.columns.index(c)
                if cidx == 0:
                    if len(c['rows']) == 1:
                        return
                    c['rows'].remove(cur)
                    self.add_column(True, cur)
                    if len(c['rows']) == 0:
                        self.columns.remove(c)
                else:
                    c['rows'].remove(cur)
                    self.columns[cidx - 1]['rows'].append(cur)
                if len(c['rows']) == 0:
                    self.columns.remove(c)
                    newwidth = int(100 / len(self.columns))
                    for c in self.columns:
                        c['width'] = newwidth
                else:
                    if c['active'] >= len(c['rows']):
                        c['active'] = len(c['rows']) - 1
                self.group.focus(cur)
                return

    def swap_column_width(self, grow, shrink):
        grower = self.columns[grow]
        shrinker = self.columns[shrink]
        amount = self.grow_amount
        if shrinker['width'] - amount < 5:
            return
        grower['width'] += amount
        shrinker['width'] -= amount

    def cmd_grow_left(self):
        cur = self.current_window
        if cur is None:
            return
        for c in self.columns:
            if cur in c['rows']:
                cidx = self.columns.index(c)
                if cidx == 0:
                    # grow left for leftmost-column, shrink left
                    if self.is_last_column(cidx):
                        return
                    self.swap_column_width(cidx + 1, cidx)
                    self.group.focus(cur)
                    return
                self.swap_column_width(cidx, cidx - 1)
                self.group.focus(cur)
                return

    def cmd_grow_right(self):
        cur = self.current_window
        if cur is None:
            return
        for c in self.columns:
            if cur in c['rows']:
                cidx = self.columns.index(c)
                if self.is_last_column(cidx):
                    # grow right from right most, shrink right
                    if cidx == 0:
                        return
                    self.swap_column_width(cidx - 1, cidx)
                    self.group.focus(cur)
                    return
                # grow my width by 20, reduce neighbor to the right by 20
                self.swap_column_width(cidx, cidx + 1)
                self.group.focus(cur)
                return

    def cmd_shuffle_right(self):
        cur = self.current_window
        if cur is None:
            return
        for c in self.columns:
            if cur in c['rows']:
                cidx = self.columns.index(c)
                if self.is_last_column(cidx):
                    if len(c['rows']) == 1:
                        return
                    c['rows'].remove(cur)
                    self.add_column(False, cur)
                    if len(c['rows']) == 0:
                        self.columns.remove(c)
                else:
                    c['rows'].remove(cur)
                    self.columns[cidx + 1]['rows'].append(cur)
                if len(c['rows']) == 0:
                    self.columns.remove(c)
                    newwidth = int(100 / len(self.columns))
                    for c in self.columns:
                        c['width'] = newwidth
                else:
                    if c['active'] >= len(c['rows']):
                        c['active'] = len(c['rows']) - 1
                self.group.focus(cur)
                return

    def cmd_shuffle_down(self):
        for c in self.columns:
            if self.current_window in c['rows']:
                r = c['rows']
                ridx = r.index(self.current_window)
                if ridx + 1 < len(r):
                    r[ridx], r[ridx + 1] = r[ridx + 1], r[ridx]
                    client = r[ridx + 1]
                    self.focus(client)
                    self.group.focus(client)
                return

    def cmd_shuffle_up(self):
        for c in self.columns:
            if self.current_window in c['rows']:
                r = c['rows']
                ridx = r.index(self.current_window)
                if ridx > 0:
                    r[ridx - 1], r[ridx] = r[ridx], r[ridx - 1]
                    client = r[ridx - 1]
                    self.focus(client)
                    self.group.focus(client)
                return
