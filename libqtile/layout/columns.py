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

class _Column(object):
    def __init__(self, autosplit=True, width=100):
        self.width = width
        self.split = autosplit
        self.current = 0
        self.clients = []
        self.heights = {}

    def info(self):
        return dict(
            clients=[c.name for c in self],
            heights=[self.heights[c] for c in self],
            split=self.split,
            current=self.current,
        )

    @property
    def cw(self):
        if len(self):
            return self.clients[self.current]
        return None

    def toggleSplit(self):
        self.split = not self.split

    def focus(self, client):
        self.current = self.index(client)

    def focus_first(self):
        if self.split and len(self):
            return self[0]
        return self.cw

    def focus_last(self):
        if self.split and len(self):
            return self[-1]
        return None

    def focus_next(self, win):
        idx = self.index(win) + 1
        if self.split and idx < len(self):
            return self[idx]
        return None

    def focus_previous(self, win):
        idx = self.index(win) - 1
        if self.split and idx >= 0:
            return self[idx]
        return None

    def add(self, client, height=100):
        self.clients.insert(self.current, client)
        self.heights[client] = height
        delta = 100 - height
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def remove(self, client):
        idx = self.index(client)
        delta = self.heights[client] - 100
        del self.heights[client]
        del self.clients[idx]
        if len(self) == 0:
            self.current = 0
            return
        elif idx <= self.current:
            self.current = max(0, self.current - 1)
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def index(self, client):
        return self.clients.index(client)

    def __len__(self):
        return len(self.clients)

    def __getitem__(self, i):
        return self.clients[i]

    def __setitem__(self, i, c):
        self.clients[i] = c

    def __contains__(self, client):
        return client in self.clients

    def __str__(self):
        cur = self.current
        return "_Column: " + ", ".join([
            "[%s: %d]" % (c.name, self.heights[c]) if c == cur else
            "%s: %d" % (c.name, self.heights[c]) for c in self
        ])


class Columns(Layout):
    """Extension of the Stack layout.

    The screen is split into columns, which can be dynamically added or
    removed.  Each column displays either a sigle window at a time from a
    stack of windows or all of them simultaneously, spliting the column
    space.  Columns and windows can be resized and windows can be shuffled
    around.  This layout can also emulate "Wmii", "Verical", and "Max",
    depending on the default parameters.

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
        ("border_width", 2, "Border width."),
        ("margin", 0, "Margin of the layout."),
        ("autosplit", True, "Autosplit newly created columns."),
        ("num_columns", 2, "Preferred number of columns."),
        ("grow_amount", 10, "Amount by which to grow a window/column."),
        ("fair", False, "Add new windows to the column with least windows."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Columns.defaults)
        self.columns = [_Column(self.autosplit)]
        self.current = 0

    def clone(self, group):
        c = Layout.clone(self, group)
        c.columns = [_Column(self.autosplit)]
        return c

    def info(self):
        d = Layout.info(self)
        d["columns"] = [c.info() for c in self.columns]
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
        c = _Column(self.autosplit)
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
            color = self.group.qtile.colorPixel(self.border_focus)
        else:
            color = self.group.qtile.colorPixel(self.border_normal)
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
            height = int(0.5 + col.heights[client] * screen.height * 0.01 /
                    len(col))
            y = screen.y + int(0.5 + pos * screen.height * 0.01 / len(col))
            client.place(x, y, width - 2 * border,
                    height - 2 * border, border,
                    color, margin=self.margin)
            client.unhide()
        elif client == col.cw:
            client.place(x, screen.y, width - 2 * border,
                    screen.height - 2 * border, border,
                    color, margin=self.margin)
            client.unhide()
        else:
            client.hide()

    def focus_first(self):
        return self.cc.focus_first()

    def focus_last(self):
        return self.cc.focus_last()

    def focus_next(self, win):
        for col in self.columns:
            if win in col:
                return col.focus_next(win)

    def focus_previous(self, win):
        for col in self.columns:
            if win in col:
                return col.focus_previous(win)

    def cmd_toggle_split(self):
        self.cc.toggleSplit()
        self.group.layoutAll()

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
            col.current = (col.current - 1) % len(col)
            self.group.focus(col.cw, True)

    def cmd_down(self):
        col = self.cc
        if len(col) > 1:
            col.current = (col.current + 1) % len(col)
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
        self.group.layoutAll()

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
        self.group.layoutAll()

    def cmd_shuffle_up(self):
        col = self.cc
        if col.current > 0:
            col[col.current], col[col.current - 1] = \
                col[col.current - 1], col[col.current]
            col.current -= 1
            self.group.layoutAll()

    def cmd_shuffle_down(self):
        col = self.cc
        if col.current + 1 < len(col):
            col[col.current], col[col.current + 1] = \
                col[col.current + 1], col[col.current]
            col.current += 1
            self.group.layoutAll()

    def cmd_grow_left(self):
        if self.current > 0:
            if self.columns[self.current - 1].width > self.grow_amount:
                self.columns[self.current - 1].width -= self.grow_amount
                self.cc.width += self.grow_amount
                self.group.layoutAll()

    def cmd_grow_right(self):
        if self.current + 1 < len(self.columns):
            if self.columns[self.current + 1].width > self.grow_amount:
                self.columns[self.current + 1].width -= self.grow_amount
                self.cc.width += self.grow_amount
                self.group.layoutAll()

    def cmd_grow_up(self):
        col = self.cc
        if col.current > 0:
            if col.heights[col[col.current - 1]] > self.grow_amount:
                col.heights[col[col.current - 1]] -= self.grow_amount
                col.heights[col.cw] += self.grow_amount
                self.group.layoutAll()

    def cmd_grow_down(self):
        col = self.cc
        if col.current + 1 < len(col):
            if col.heights[col[col.current + 1]] > self.grow_amount:
                col.heights[col[col.current + 1]] -= self.grow_amount
                col.heights[col.cw] += self.grow_amount
                self.group.layoutAll()

    def cmd_normalize(self):
        for col in self.columns:
            for client in col:
                col.heights[client] = 100
            col.width = 100
        self.group.layoutAll()
