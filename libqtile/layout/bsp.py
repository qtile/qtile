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
from libqtile.layout.base import Layout


class _BspNode():
    def __init__(self, parent=None):
        self.parent = parent
        self.children = []
        self.split_horizontal = None
        self.split_ratio = 50
        self.client = None
        self.x = self.y = 0
        self.w = 16
        self.h = 9

    def __iter__(self):
        yield self
        for child in self.children:
            for c in child:
                yield c

    def clients(self):
        if self.client:
            yield self.client
        else:
            for child in self.children:
                for c in child.clients():
                    yield c

    def _shortest(self, length):
        if len(self.children) == 0:
            return self, length

        child0, length0 = self.children[0]._shortest(length + 1)
        child1, length1 = self.children[1]._shortest(length + 1)

        if length1 < length0:
            return child1, length1
        return child0, length0

    def get_shortest(self):
        return self._shortest(0)[0]

    def insert(self, client, idx, ratio):
        if self.client is None:
            self.client = client
            return self
        self.children = [_BspNode(self), _BspNode(self)]
        self.children[1 - idx].client = self.client
        self.children[idx].client = client
        self.client = None
        self.split_horizontal = True if self.w > self.h * ratio else False
        return self.children[idx]

    def remove(self, child):
        keep = self.children[1 if child is self.children[0] else 0]
        self.children = keep.children
        for c in self.children:
            c.parent = self
        self.split_horizontal = keep.split_horizontal
        self.split_ratio = keep.split_ratio
        self.client = keep.client
        return self

    def distribute(self):
        if len(self.children) == 0:
            return 1, 1
        h0, v0 = self.children[0].distribute()
        h1, v1 = self.children[1].distribute()
        if self.split_horizontal:
            h = h0 + h1
            v = max(v0, v1)
            self.split_ratio = 100 * h0 / h
        else:
            h = max(h0, h1)
            v = v0 + v1
            self.split_ratio = 100 * v0 / v
        return h, v

    def calc_geom(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        if len(self.children) > 1:
            if self.split_horizontal:
                w0 = int(self.split_ratio * w * 0.01 + 0.5)
                self.children[0].calc_geom(x, y, w0, h)
                self.children[1].calc_geom(x + w0, y, w - w0, h)
            else:
                h0 = int(self.split_ratio * h * 0.01 + 0.5)
                self.children[0].calc_geom(x, y, w, h0)
                self.children[1].calc_geom(x, y + h0, w, h - h0)


class Bsp(Layout):
    """This layout is inspired by bspwm, but it does not try to copy its
    features.

    The first client occupies the entire screen space.  When a new client
    is created, the selected space is partitioned in 2 and the new client
    occupies one of those subspaces, leaving the old client with the other.

    The partition can be either horizontal or vertical according to the
    dimensions of the current space: if its width/height ratio is above
    a pre-configured value, the subspaces are created side-by-side,
    otherwise, they are created on top of each other.  The partition
    direction can be freely toggled.  All subspaces can be resized and
    clients can be shuffled around.

    All clients are organized at the leaves of a full binary tree.

    An example key configuration is::

        Key([mod], "j", lazy.layout.down()),
        Key([mod], "k", lazy.layout.up()),
        Key([mod], "h", lazy.layout.left()),
        Key([mod], "l", lazy.layout.right()),
        Key([mod, "shift"], "j", lazy.layout.shuffle_down()),
        Key([mod, "shift"], "k", lazy.layout.shuffle_up()),
        Key([mod, "shift"], "h", lazy.layout.shuffle_left()),
        Key([mod, "shift"], "l", lazy.layout.shuffle_right()),
        Key([mod, "mod1"], "j", lazy.layout.flip_down()),
        Key([mod, "mod1"], "k", lazy.layout.flip_up()),
        Key([mod, "mod1"], "h", lazy.layout.flip_left()),
        Key([mod, "mod1"], "l", lazy.layout.flip_right()),
        Key([mod, "control"], "j", lazy.layout.grow_down()),
        Key([mod, "control"], "k", lazy.layout.grow_up()),
        Key([mod, "control"], "h", lazy.layout.grow_left()),
        Key([mod, "control"], "l", lazy.layout.grow_right()),
        Key([mod, "shift"], "n", lazy.layout.normalize()),
        Key([mod], "Return", lazy.layout.toggle_split()),
    """
    defaults = [
        ("border_focus", "#881111", "Border colour(s) for the focused window."),
        ("border_normal", "#220000", "Border colour(s) for un-focused windows."),
        ("border_width", 2, "Border width."),
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])."),
        ("ratio", 1.6,
         "Width/height ratio that defines the partition direction."),
        ("grow_amount", 10, "Amount by which to grow a window/column."),
        ("lower_right", True, "New client occupies lower or right subspace."),
        ("fair", True, "New clients are inserted in the shortest branch."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Bsp.defaults)
        self.root = _BspNode()
        self.current = self.root

    def clone(self, group):
        c = Layout.clone(self, group)
        c.root = _BspNode()
        c.current = c.root
        return c

    def info(self):
        return dict(
            name=self.name,
            clients=[c.name for c in self.root.clients()])

    def get_node(self, client):
        for node in self.root:
            if client is node.client:
                return node

    def focus(self, client):
        self.current = self.get_node(client)

    def add(self, client):
        node = self.root.get_shortest() if self.fair else self.current
        self.current = node.insert(client, int(self.lower_right), self.ratio)

    def remove(self, client):
        node = self.get_node(client)
        if node:
            if node.parent:
                node = node.parent.remove(node)
                newclient = next(node.clients(), None)
                if newclient is None:
                    self.current = self.root
                else:
                    self.current = self.get_node(newclient)
                return newclient
            node.client = None
            self.current = self.root

    def configure(self, client, screen_rect):
        self.root.calc_geom(screen_rect.x, screen_rect.y, screen_rect.width,
                            screen_rect.height)
        node = self.get_node(client)
        color = self.border_focus if client.has_focus else self.border_normal
        border = 0 if node is self.root else self.border_width
        if node is not None:
            client.place(
                node.x,
                node.y,
                node.w - 2 * border,
                node.h - 2 * border,
                border,
                color,
                margin=self.margin)
        client.unhide()

    def cmd_toggle_split(self):
        if self.current.parent:
            self.current.parent.split_horizontal = not self.current.parent.split_horizontal
        self.group.layout_all()

    def focus_first(self):
        return next(self.root.clients(), None)

    def focus_last(self):
        clients = list(self.root.clients())
        return clients[-1] if len(clients) else None

    def focus_next(self, client):
        clients = list(self.root.clients())
        if client in clients:
            idx = clients.index(client)
            if idx + 1 < len(clients):
                return clients[idx + 1]

    def focus_previous(self, client):
        clients = list(self.root.clients())
        if client in clients:
            idx = clients.index(client)
            if idx > 0:
                return clients[idx - 1]

    def cmd_next(self):
        client = self.focus_next(self.current)
        if client:
            self.group.focus(client, True)

    def cmd_previous(self):
        client = self.focus_previous(self.current)
        if client:
            self.group.focus(client, True)

    def find_left(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[1]:
                neighbor = parent.children[0]
                center = self.current.y + self.current.h * 0.5
                while neighbor.client is None:
                    if neighbor.split_horizontal or neighbor.children[1].y < center:
                        neighbor = neighbor.children[1]
                    else:
                        neighbor = neighbor.children[0]
                return neighbor
            child = parent
            parent = child.parent

    def find_right(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[0]:
                neighbor = parent.children[1]
                center = self.current.y + self.current.h * 0.5
                while neighbor.client is None:
                    if neighbor.split_horizontal or neighbor.children[1].y > center:
                        neighbor = neighbor.children[0]
                    else:
                        neighbor = neighbor.children[1]
                return neighbor
            child = parent
            parent = child.parent

    def find_up(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[1]:
                neighbor = parent.children[0]
                center = self.current.x + self.current.w * 0.5
                while neighbor.client is None:
                    if not neighbor.split_horizontal or neighbor.children[1].x < center:
                        neighbor = neighbor.children[1]
                    else:
                        neighbor = neighbor.children[0]
                return neighbor
            child = parent
            parent = child.parent

    def find_down(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[0]:
                neighbor = parent.children[1]
                center = self.current.x + self.current.w * 0.5
                while neighbor.client is None:
                    if not neighbor.split_horizontal or neighbor.children[1].x > center:
                        neighbor = neighbor.children[0]
                    else:
                        neighbor = neighbor.children[1]
                return neighbor
            child = parent
            parent = child.parent

    def cmd_left(self):
        node = self.find_left()
        if node:
            self.group.focus(node.client, True)

    def cmd_right(self):
        node = self.find_right()
        if node:
            self.group.focus(node.client, True)

    def cmd_up(self):
        node = self.find_up()
        if node:
            self.group.focus(node.client, True)

    def cmd_down(self):
        node = self.find_down()
        if node:
            self.group.focus(node.client, True)

    def cmd_shuffle_left(self):
        node = self.find_left()
        if node:
            node.client, self.current.client = self.current.client, node.client
            self.current = node
            self.group.layout_all()
        elif self.current is not self.root:
            node = self.current
            self.remove(node.client)
            newroot = _BspNode()
            newroot.split_horizontal = True
            newroot.children = [node, self.root]
            self.root.parent = newroot
            node.parent = newroot
            self.root = newroot
            self.current = node
            self.group.layout_all()

    def cmd_shuffle_right(self):
        node = self.find_right()
        if node:
            node.client, self.current.client = self.current.client, node.client
            self.current = node
            self.group.layout_all()
        elif self.current is not self.root:
            node = self.current
            self.remove(node.client)
            newroot = _BspNode()
            newroot.split_horizontal = True
            newroot.children = [self.root, node]
            self.root.parent = newroot
            node.parent = newroot
            self.root = newroot
            self.current = node
            self.group.layout_all()

    def cmd_shuffle_up(self):
        node = self.find_up()
        if node:
            node.client, self.current.client = self.current.client, node.client
            self.current = node
            self.group.layout_all()
        elif self.current is not self.root:
            node = self.current
            self.remove(node.client)
            newroot = _BspNode()
            newroot.split_horizontal = False
            newroot.children = [node, self.root]
            self.root.parent = newroot
            node.parent = newroot
            self.root = newroot
            self.current = node
            self.group.layout_all()

    def cmd_shuffle_down(self):
        node = self.find_down()
        if node:
            node.client, self.current.client = self.current.client, node.client
            self.current = node
            self.group.layout_all()
        elif self.current is not self.root:
            node = self.current
            self.remove(node.client)
            newroot = _BspNode()
            newroot.split_horizontal = False
            newroot.children = [self.root, node]
            self.root.parent = newroot
            node.parent = newroot
            self.root = newroot
            self.current = node
            self.group.layout_all()

    def cmd_grow_left(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[1]:
                parent.split_ratio = max(5,
                                         parent.split_ratio - self.grow_amount)
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_grow_right(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[0]:
                parent.split_ratio = min(95,
                                         parent.split_ratio + self.grow_amount)
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_grow_up(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[1]:
                parent.split_ratio = max(5,
                                         parent.split_ratio - self.grow_amount)
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_grow_down(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[0]:
                parent.split_ratio = min(95,
                                         parent.split_ratio + self.grow_amount)
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_flip_left(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[1]:
                parent.children = parent.children[::-1]
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_flip_right(self):
        child = self.current
        parent = child.parent
        while parent:
            if parent.split_horizontal and child is parent.children[0]:
                parent.children = parent.children[::-1]
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_flip_up(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[1]:
                parent.children = parent.children[::-1]
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_flip_down(self):
        child = self.current
        parent = child.parent
        while parent:
            if not parent.split_horizontal and child is parent.children[0]:
                parent.children = parent.children[::-1]
                self.group.layout_all()
                break
            child = parent
            parent = child.parent

    def cmd_normalize(self):
        distribute = True
        for node in self.root:
            if node.split_ratio != 50:
                node.split_ratio = 50
                distribute = False
        if distribute:
            self.root.distribute()
        self.group.layout_all()
