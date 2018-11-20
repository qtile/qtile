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

from .base import Layout, _ClientList


class _Column(_ClientList):

    # shortcuts for current client and index used in Columns layout
    cw = _ClientList.current_client
    current = _ClientList.current_index

    def __init__(self, split, insert_position, width=100):
        _ClientList.__init__(self)
        self.width = width
        self.split = split
        self.insert_position = insert_position
        self.heights = {}

    def info(self):
        info = _ClientList.info(self)
        info.update(
            dict(
                heights=[self.heights[c] for c in self.clients],
                split=self.split,
            ))
        return info

    def toggleSplit(self):
        self.split = not self.split

    def add(self, client, height=100):
        _ClientList.add(self, client, self.insert_position)
        self.heights[client] = height
        delta = 100 - height
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def remove(self, client):
        _ClientList.remove(self, client)
        delta = self.heights[client] - 100
        del self.heights[client]
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def __str__(self):
        cur = self.current
        return "_Column: " + ", ".join([
            "[%s: %d]" % (c.name, self.heights[c])
            if c == cur else "%s: %d" % (c.name, self.heights[c])
            for c in self.clients
        ])


class Columns(Layout):
    """Extension of the Stack layout.

    The screen is split into columns, which can be dynamically added or
    removed.  Each column can present is windows in 2 modes: split or
    stacked.  In split mode, all windows are presented simultaneously,
    spliting the column space.  In stacked mode, only a single window is
    presented from the stack of windows.  Columns and windows can be
    resized and windows can be shuffled around.

    This layout can also emulate "Wmii", "Vertical", and "Max", depending
    on the default parameters.

    An example key configuration is::

        Key([mod], "j", lazy.layout.down()),
        Key([mod], "k", lazy.layout.up()),
        Key([mod], "h", lazy.layout.left()),
        Key([mod], "l", lazy.layout.right()),
        Key([mod, "shift"], "j", lazy.layout.shuffle_down()),
        Key([mod, "shift"], "k", lazy.layout.shuffle_up()),
        Key([mod, "shift"], "h", lazy.layout.shuffle_left()),
        Key([mod, "shift"], "l", lazy.layout.shuffle_right()),
        Key([mod, "control"], "j", lazy.layout.grow_down()),
        Key([mod, "control"], "k", lazy.layout.grow_up()),
        Key([mod, "control"], "h", lazy.layout.grow_left()),
        Key([mod, "control"], "l", lazy.layout.grow_right()),
        Key([mod], "Return", lazy.layout.toggle_split()),
        Key([mod], "n", lazy.layout.normalize()),
    """
    defaults = [
        ("name", "columns", "Name of this layout."),
        ("border_focus", "#881111", "Border colour for the focused window."),
        ("border_normal", "#220000", "Border colour for un-focused windows."),
        ("border_focus_stack", "#881111",
         "Border colour for the focused window in stacked columns."),
        ("border_normal_stack", "#220000",
         "Border colour for un-focused windows in stacked columns."),
        ("border_width", 2, "Border width."),
        ("margin", 0, "Margin of the layout."),
        ("split", True, "New columns presentation mode."),
        ("num_columns", 2, "Preferred number of columns."),
        ("grow_amount", 10, "Amount by which to grow a window/column."),
        ("fair", False, "Add new windows to the column with least windows."),
        ("insert_position", 0,
         "Position relative to the current window where new ones are inserted "
         "(0 means right above the current window, 1 means right after)."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Columns.defaults)
        self.columns = [_Column(self.split, self.insert_position)]
        self.current = 0

    def clone(self, group):
        c = Layout.clone(self, group)
        c.columns = [_Column(self.split, self.insert_position)]
        return c

    def info(self):
        d = Layout.info(self)
        d["clients"] = []
        d["columns"] = []
        for c in self.columns:
            cinfo = c.info()
            d["clients"].extend(cinfo['clients'])
            d["columns"].append(cinfo)
        d["current"] = self.current
        return d

    def focus(self, client):
        for i, c in enumerate(self.columns):
            if client in c:
                c.focus(client)
                self.current = i
                break

    @property
    def cc(self):
        return self.columns[self.current]

    def add_column(self, prepend=False):
        c = _Column(self.split, self.insert_position)
        if prepend:
            self.columns.insert(0, c)
            self.current += 1
        else:
            self.columns.append(c)
        return c

    def remove_column(self, col):
        idx = self.columns.index(col)
        del self.columns[idx]
        if idx <= self.current:
            self.current = max(0, self.current - 1)
        delta = col.width - 100
        if delta != 0:
            n = len(self.columns)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self.columns, growth):
                c.width += g

    def add(self, client):
        c = self.cc
        if len(c) > 0 and len(self.columns) < self.num_columns:
            c = self.add_column()
        if self.fair:
            least = min(self.columns, key=len)
            if len(least) < len(c):
                c = least
        self.current = self.columns.index(c)
        c.add(client)

    def remove(self, client):
        remove = None
        for c in self.columns:
            if client in c:
                c.remove(client)
                if len(c) == 0 and len(self.columns) > 1:
                    remove = c
                break
        if remove is not None:
            self.remove_column(c)
        return self.columns[self.current].cw

    def configure(self, client, screen):
        pos = 0
        for col in self.columns:
            if client in col:
                break
            pos += col.width
        else:
            client.hide()
            return
        if client.has_focus:
            color = self.group.qtile.color_pixel(self.border_focus if col.split
                                                 else self.border_focus_stack)
        else:
            color = self.group.qtile.color_pixel(self.border_normal if col.split
                                                 else self.border_normal_stack)
        if len(self.columns) == 1 and (len(col) == 1 or not col.split):
            border = 0
        else:
            border = self.border_width
        width = int(0.5 + col.width * screen.width * 0.01 / len(self.columns))
        x = screen.x + int(0.5 + pos * screen.width * 0.01 / len(self.columns))
        if col.split:
            pos = 0
            for c in col:
                if client == c:
                    break
                pos += col.heights[c]
            height = int(
                0.5 + col.heights[client] * screen.height * 0.01 / len(col))
            y = screen.y + int(0.5 + pos * screen.height * 0.01 / len(col))
            client.place(
                x,
                y,
                width - 2 * border,
                height - 2 * border,
                border,
                color,
                margin=self.margin)
            client.unhide()
        elif client == col.cw:
            client.place(
                x,
                screen.y,
                width - 2 * border,
                screen.height - 2 * border,
                border,
                color,
                margin=self.margin)
            client.unhide()
        else:
            client.hide()

    def focus_first(self):
        """Returns first client in first column of layout"""
        if self.columns:
            return self.columns[0].focus_first()

    def focus_last(self):
        """Returns last client in last column of layout"""
        if self.columns:
            return self.columns[-1].focus_last()

    def focus_next(self, win):
        """Returns the next client after 'win' in layout,
           or None if there is no such client"""
        # First: try to get next window in column of win
        for idx, col in enumerate(self.columns):
            if win in col:
                nxt = col.focus_next(win)
                if nxt:
                    return nxt
                else:
                    break
        # if there was no next, get first client from next column
        if idx + 1 < len(self.columns):
            return self.columns[idx + 1].focus_first()

    def focus_previous(self, win):
        """Returns the client previous to 'win' in layout.
           or None if there is no such client"""
        # First: try to focus previous client in column
        for idx, col in enumerate(self.columns):
            if win in col:
                prev = col.focus_previous(win)
                if prev:
                    return prev
                else:
                    break
        # If there was no previous, get last from previous column
        if idx > 0:
            return self.columns[idx - 1].focus_last()

    def cmd_toggle_split(self):
        self.cc.toggleSplit()
        self.group.layout_all()

    def cmd_left(self):
        if len(self.columns) > 1:
            self.current = (self.current - 1) % len(self.columns)
            self.group.focus(self.cc.cw, True)

    def cmd_right(self):
        if len(self.columns) > 1:
            self.current = (self.current + 1) % len(self.columns)
            self.group.focus(self.cc.cw, True)

    def cmd_up(self):
        col = self.cc
        if len(col) > 1:
            col.current_index -= 1
            self.group.focus(col.cw, True)

    def cmd_down(self):
        col = self.cc
        if len(col) > 1:
            col.current_index += 1
            self.group.focus(col.cw, True)

    def cmd_next(self):
        if self.cc.split and self.cc.current < len(self.cc) - 1:
            self.cc.current += 1
        elif self.columns:
            self.current = (self.current + 1) % len(self.columns)
            if self.cc.split:
                self.cc.current = 0
        self.group.focus(self.cc.cw, True)

    def cmd_previous(self):
        if self.cc.split and self.cc.current > 0:
            self.cc.current -= 1
        elif self.columns:
            self.current = (self.current - 1) % len(self.columns)
            if self.cc.split:
                self.cc.current = len(self.cc) - 1
        self.group.focus(self.cc.cw, True)

    def cmd_shuffle_left(self):
        cur = self.cc
        client = cur.cw
        if client is None:
            return
        if self.current > 0:
            self.current -= 1
            new = self.cc
            new.add(client, cur.heights[client])
            cur.remove(client)
            if len(cur) == 0:
                self.remove_column(cur)
        elif len(cur) > 1:
            new = self.add_column(True)
            new.add(client, cur.heights[client])
            cur.remove(client)
            self.current = 0
        else:
            return
        self.group.layout_all()

    def cmd_shuffle_right(self):
        cur = self.cc
        client = cur.cw
        if client is None:
            return
        if self.current + 1 < len(self.columns):
            self.current += 1
            new = self.cc
            new.add(client, cur.heights[client])
            cur.remove(client)
            if len(cur) == 0:
                self.remove_column(cur)
        elif len(cur) > 1:
            new = self.add_column()
            new.add(client, cur.heights[client])
            cur.remove(client)
            self.current = len(self.columns) - 1
        else:
            return
        self.group.layout_all()

    def cmd_shuffle_up(self):
        if self.cc.current_index > 0:
            self.cc.shuffle_up()
            self.group.layout_all()

    def cmd_shuffle_down(self):
        if self.cc.current_index + 1 < len(self.cc):
            self.cc.shuffle_down()
            self.group.layout_all()

    def cmd_grow_left(self):
        if self.current > 0:
            if self.columns[self.current - 1].width > self.grow_amount:
                self.columns[self.current - 1].width -= self.grow_amount
                self.cc.width += self.grow_amount
                self.group.layout_all()

    def cmd_grow_right(self):
        if self.current + 1 < len(self.columns):
            if self.columns[self.current + 1].width > self.grow_amount:
                self.columns[self.current + 1].width -= self.grow_amount
                self.cc.width += self.grow_amount
                self.group.layout_all()

    def cmd_grow_up(self):
        col = self.cc
        if col.current > 0:
            if col.heights[col[col.current - 1]] > self.grow_amount:
                col.heights[col[col.current - 1]] -= self.grow_amount
                col.heights[col.cw] += self.grow_amount
                self.group.layout_all()

    def cmd_grow_down(self):
        col = self.cc
        if col.current + 1 < len(col):
            if col.heights[col[col.current + 1]] > self.grow_amount:
                col.heights[col[col.current + 1]] -= self.grow_amount
                col.heights[col.cw] += self.grow_amount
                self.group.layout_all()

    def cmd_normalize(self):
        for col in self.columns:
            for client in col:
                col.heights[client] = 100
            col.width = 100
        self.group.layout_all()
