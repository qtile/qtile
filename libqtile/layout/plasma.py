# Copyright (c) 2017 numirias
# Copyright (c) 2024 elParaguayo
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
import copy
import time
from enum import Enum, Flag, auto
from math import isclose
from typing import NamedTuple

from libqtile import hook
from libqtile.backend.base import Window
from libqtile.command.base import expose_command
from libqtile.hook import Hook, qtile_hooks
from libqtile.layout.base import Layout

plasma_hook = Hook(
    "plasma_add_mode",
    """
    Used to flag when the add mode of the Plasma layout has changed.

    The hooked function should take one argument being the layout object.
    """,
)


qtile_hooks.register_hook(plasma_hook)


class NotRestorableError(Exception):
    pass


class Point(NamedTuple):
    x: int
    y: int


class Dimensions(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class Orient(Flag):
    HORIZONTAL = 0
    VERTICAL = 1


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def orient(self):
        return Orient.HORIZONTAL if self in [self.LEFT, self.RIGHT] else Orient.VERTICAL

    @property
    def offset(self):
        return 1 if self in [self.RIGHT, self.DOWN] else -1


class Priority(Enum):
    FIXED = auto()
    BALANCED = auto()


class AddMode(Flag):
    HORIZONTAL = auto()
    VERTICAL = auto()
    SPLIT = auto()

    @property
    def orient(self):
        return Orient.VERTICAL if self & self.VERTICAL else Orient.HORIZONTAL


border_check = {
    Direction.UP: lambda a, b: isclose(a.y, b.y_end),
    Direction.DOWN: lambda a, b: isclose(a.y_end, b.y),
    Direction.LEFT: lambda a, b: isclose(a.x, b.x_end),
    Direction.RIGHT: lambda a, b: isclose(a.x_end, b.x),
}


def flatten(value):
    """Flattens a nested list of lists into a single list."""
    out = []
    for x in value:
        if not isinstance(x, list):
            out.append(x)
        else:
            out.extend(flatten(x))
    return out


class Node:
    """
    A tree node.

    Each node represents a container that can hold a payload and child nodes.
    """

    min_size_default = 100
    root_orient = Orient.HORIZONTAL
    priority = Priority.FIXED

    def __init__(self, payload=None, x=None, y=None, width=None, height=None):
        self.payload = payload
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._size = None
        self.children = []
        self.last_accessed = 0
        self.parent = None
        self.restorables = {}

    def __repr__(self):
        info = self.payload or ""
        if self:
            info += f" +{len(self):d}"
        return f"<Node {info} {id(self):x}>"

    # Define dunder methods to treat Node objects like an iterable
    def __contains__(self, node):
        if node is self:
            return True
        for child in self:
            if node in child:
                return True
        return False

    def __iter__(self):
        yield from self.children

    def __getitem__(self, key):
        return self.children[key]

    def __setitem__(self, key, value):
        self.children[key] = value

    def __len__(self):
        return len(self.children)

    @property
    def root(self):
        try:
            # Walk way up the tree until we find the root
            return self.parent.root
        except AttributeError:
            # Node has no parent (self.parent is None) so node must be root
            return self

    @property
    def is_root(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self.children

    @property
    def index(self):
        return self.parent.children.index(self)

    @property
    def tree(self):
        return [c.tree if c else c for c in self]

    @property
    def siblings(self):
        if self.is_root:
            return list()
        return [c for c in self.parent if c is not self]

    @property
    def first_leaf(self):
        if self.is_leaf:
            return self
        return self[0].first_leaf

    @property
    def last_leaf(self):
        if self.is_leaf:
            return self
        return self[-1].last_leaf

    @property
    def recent_leaf(self):
        if self.is_leaf:
            return self
        return max(self, key=lambda n: n.last_accessed).recent_leaf

    @property
    def prev_leaf(self):
        if self.is_root:
            return self.last_leaf
        idx = self.index - 1
        if idx < 0:
            return self.parent.prev_leaf
        return self.parent[idx].last_leaf

    @property
    def next_leaf(self):
        if self.is_root:
            return self.first_leaf
        idx = self.index + 1
        if idx >= len(self.parent):
            return self.parent.next_leaf
        return self.parent[idx].first_leaf

    @property
    def all_leafs(self):
        if self.is_leaf:
            yield self
        for child in self:
            yield from child.all_leafs

    @property
    def orient(self):
        if self.is_root:
            return self.root_orient
        return ~self.parent.orient

    @property
    def horizontal(self):
        return self.orient is Orient.HORIZONTAL

    @property
    def vertical(self):
        return self.orient is Orient.VERTICAL

    @property
    def x(self):
        if self.is_root:
            return self._x
        if self.horizontal:
            return self.parent.x
        return self.parent.x + self.size_offset

    @x.setter
    def x(self, val):
        if not self.is_root:
            return
        self._x = val

    @property
    def y(self):
        if self.is_root:
            return self._y
        if self.vertical:
            return self.parent.y
        return self.parent.y + self.size_offset

    @y.setter
    def y(self, val):
        if not self.is_root:
            return
        self._y = val

    @property
    def pos(self):
        return Point(self.x, self.y)

    @property
    def width(self):
        if self.is_root:
            return self._width
        if self.horizontal:
            return self.parent.width
        return self.size

    @width.setter
    def width(self, val):
        if self.is_root:
            self._width = val
        elif self.horizontal:
            self.parent.size = val
        else:
            self.size = val

    @property
    def height(self):
        if self.is_root:
            return self._height
        if self.vertical:
            return self.parent.height
        return self.size

    @height.setter
    def height(self, val):
        if self.is_root:
            self._height = val
        elif self.vertical:
            self.parent.size = val
        else:
            self.size = val

    @property
    def x_end(self):
        return self.x + self.width

    @property
    def y_end(self):
        return self.y + self.height

    @property
    def x_center(self):
        return self.x + self.width / 2

    @property
    def y_center(self):
        return self.y + self.height / 2

    @property
    def center(self):
        return Point(self.x_center, self.y_center)

    @property
    def pixel_perfect(self):
        """
        Return pixel-perfect int dimensions (x, y, width, height) which
        compensate for gaps in the layout grid caused by plain int conversions.
        """
        x, y, width, height = self.x, self.y, self.width, self.height
        threshold = 0.99999
        if (x - int(x)) + (width - int(width)) > threshold:
            width += 1
        if (y - int(y)) + (height - int(height)) > threshold:
            height += 1
        return Dimensions(*map(int, (x, y, width, height)))

    @property
    def capacity(self):
        return self.width if self.horizontal else self.height

    @property
    def size(self):
        """Return amount of space taken in parent container."""
        if self.is_root:
            return None
        if self.fixed:
            return self._size
        if self.flexible:
            # Distribute space evenly among flexible nodes
            taken = sum(n.size for n in self.siblings if not n.flexible)
            flexibles = [n for n in self.parent if n.flexible]
            return (self.parent.capacity - taken) / len(flexibles)
        return max(sum(gc.min_size for gc in c) for c in self)

    @size.setter
    def size(self, val):
        if self.is_root or not self.siblings:
            return
        if val is None:
            self.reset_size()
            return
        occupied = sum(s.min_size_bound for s in self.siblings)
        val = max(min(val, self.parent.capacity - occupied), self.min_size_bound)
        self.force_size(val)

    def force_size(self, val):
        """Set size without considering available space."""
        Node.fit_into(self.siblings, self.parent.capacity - val)
        if val == 0:
            return
        if self:
            Node.fit_into([self], val)
        self._size = val

    @property
    def size_offset(self):
        return sum(c.size for c in self.parent[: self.index])

    @staticmethod
    def fit_into(nodes, space):
        """Resize nodes to fit them into the available space."""
        if not nodes:
            return
        occupied = sum(n.min_size for n in nodes)
        if space >= occupied and any(n.flexible for n in nodes):
            # If any flexible node exists, it will occupy the space
            # automatically, not requiring any action.
            return
        nodes_left = nodes[:]
        space_left = space
        if space < occupied:
            for node in nodes:
                if node.min_size_bound != node.min_size:
                    continue
                # Substract nodes that are already at their minimal possible
                # size because they can't be shrinked any further.
                space_left -= node.min_size
                nodes_left.remove(node)
        if not nodes_left:
            return
        factor = space_left / sum(n.size for n in nodes_left)
        for node in nodes_left:
            new_size = node.size * factor
            if node.fixed:
                node._size = new_size  # pylint: disable=protected-access
            for child in node:
                Node.fit_into(child, new_size)

    @property
    def fixed(self):
        """A node is fixed if it has a specified size."""
        return self._size is not None

    @property
    def min_size(self):
        if self.fixed:
            return self._size
        if self.is_leaf:
            return self.min_size_default
        size = max(sum(gc.min_size for gc in c) for c in self)
        return max(size, self.min_size_default)

    @property
    def min_size_bound(self):
        if self.is_leaf:
            return self.min_size_default
        return max(sum(gc.min_size_bound for gc in c) or self.min_size_default for c in self)

    def reset_size(self):
        self._size = None

    @property
    def flexible(self):
        """
        A node is flexible if its size isn't (explicitly or implicitly)
        determined.
        """
        if self.fixed:
            return False
        return all((any(gc.flexible for gc in c) or c.is_leaf) for c in self)

    def access(self):
        self.last_accessed = time.time()
        try:
            self.parent.access()
        except AttributeError:
            pass

    def neighbor(self, direction):
        """Return adjacent leaf node in specified direction."""
        if self.is_root:
            return None
        if direction.orient is self.parent.orient:
            target_idx = self.index + direction.offset
            if 0 <= target_idx < len(self.parent):
                return self.parent[target_idx].recent_leaf
            if self.parent.is_root:
                return None
            return self.parent.parent.neighbor(direction)
        return self.parent.neighbor(direction)

    @property
    def up(self):
        return self.neighbor(Direction.UP)

    @property
    def down(self):
        return self.neighbor(Direction.DOWN)

    @property
    def left(self):
        return self.neighbor(Direction.LEFT)

    @property
    def right(self):
        return self.neighbor(Direction.RIGHT)

    def common_border(self, node, direction):
        """Return whether a common border with given node in specified
        direction exists.
        """
        if not border_check[direction](self, node):
            return False
        if direction in [Direction.UP, Direction.DOWN]:
            detached = node.x >= self.x_end or node.x_end <= self.x
        else:
            detached = node.y >= self.y_end or node.y_end <= self.y
        return not detached

    def close_neighbor(self, direction):
        """Return visually adjacent leaf node in specified direction."""
        nodes = [n for n in self.root.all_leafs if self.common_border(n, direction)]
        if not nodes:
            return None
        most_recent = max(nodes, key=lambda n: n.last_accessed)
        if most_recent.last_accessed > 0:
            return most_recent
        if direction in [Direction.UP, Direction.DOWN]:
            match = lambda n: n.x <= self.x_center <= n.x_end  # noqa: E731
        else:
            match = lambda n: n.y <= self.y_center <= n.y_end  # noqa: E731
        return next(n for n in nodes if match(n))

    @property
    def close_up(self):
        return self.close_neighbor(Direction.UP)

    @property
    def close_down(self):
        return self.close_neighbor(Direction.DOWN)

    @property
    def close_left(self):
        return self.close_neighbor(Direction.LEFT)

    @property
    def close_right(self):
        return self.close_neighbor(Direction.RIGHT)

    def add_child(self, node, idx=None):
        if idx is None:
            idx = len(self)
        self.children.insert(idx, node)
        node.parent = self
        if len(self) == 1:
            return
        total = self.capacity
        if Node.priority is Priority.FIXED:
            # Prioritising windows with fixed sizes means the most space the siblings
            # must fit into is total width less the minimum size for a new node.
            # However, the new node doesn't have a fixed size so will expand to fit
            # available space
            space = total - Node.min_size_default
        else:
            # Balanced approach means that space for existing nodes is reduced so that
            # all nodes would be distributed evenly if none had fixed widths
            space = total - (total / len(self))
        Node.fit_into(node.siblings, space)

    def add_child_after(self, new, old):
        self.add_child(new, idx=old.index + 1)

    def remove_child(self, node):
        node._save_restore_state()  # pylint: disable=W0212
        node.force_size(0)
        self.children.remove(node)
        if len(self) == 1:
            child = self[0]
            if self.is_root:
                # A single child doesn't need a fixed size
                child.reset_size()
            else:
                # Collapse tree with a single child
                self.parent.replace_child(self, child)
                Node.fit_into(child, self.capacity)

    def remove(self):
        self.parent.remove_child(self)

    def replace_child(self, old, new):
        self[old.index] = new
        new.parent = self
        new._size = old._size  # pylint: disable=protected-access

    def flip_with(self, node, reverse=False):
        """Join with node in a new, orthogonal container."""
        container = Node()
        self.parent.replace_child(self, container)
        self.reset_size()
        for child in [node, self] if reverse else [self, node]:
            container.add_child(child)

    def add_node(self, node, mode=None):
        """Add node according to the mode.

        This can result in adding it as a child, joining with it in a new
        flipped sub-container, or splitting the space with it.
        """
        if self.is_root:
            self.add_child(node)
        elif mode is None:
            self.parent.add_child_after(node, self)
        elif mode.orient is self.parent.orient:
            if mode & AddMode.SPLIT:
                node._size = 0  # pylint: disable=protected-access
                self.parent.add_child_after(node, self)
                self._size = node._size = self.size / 2
            else:
                self.parent.add_child_after(node, self)
        else:
            self.flip_with(node)

    def restore(self, node):
        """Restore node.

        Try to add the node in a place where a node with the same payload
        has previously been.
        """
        restorables = self.root.restorables
        try:
            parent, idx, sizes, fixed, flip = restorables[node.payload]
        except KeyError:
            raise NotRestorableError()  # pylint: disable=raise-missing-from
        if parent not in self.root:
            # Don't try to restore if parent is not part of the tree anymore
            raise NotRestorableError()
        node.reset_size()
        if flip:
            old_parent_size = parent.size
            parent.flip_with(node, reverse=(idx == 0))
            node.size, parent.size = sizes
            Node.fit_into(parent, old_parent_size)
        else:
            parent.add_child(node, idx=idx)
            node.size = sizes[0]
            if len(sizes) == 2:
                node.siblings[0].size = sizes[1]
        if not fixed:
            node.reset_size()
        del restorables[node.payload]

    def _save_restore_state(self):
        parent = self.parent
        sizes = (self.size,)
        flip = False
        if len(self.siblings) == 1:
            # If there is only one node left in the container, we need to save
            # its size too because the size will be lost.
            sizes += (self.siblings[0]._size,)  # pylint: disable=W0212
            if not self.parent.is_root:
                flip = True
                parent = self.siblings[0]
        self.root.restorables[self.payload] = (parent, self.index, sizes, self.fixed, flip)

    def move(self, direction):
        """Move this node in `direction`. Return whether node was moved."""
        if self.is_root:
            return False
        if direction.orient is self.parent.orient:
            old_idx = self.index
            new_idx = old_idx + direction.offset
            if 0 <= new_idx < len(self.parent):
                p = self.parent
                p[old_idx], p[new_idx] = p[new_idx], p[old_idx]
                return True
            new_sibling = self.parent.parent
        else:
            new_sibling = self.parent
        try:
            new_parent = new_sibling.parent
            idx = new_sibling.index
        except AttributeError:
            return False
        self.reset_size()
        self.parent.remove_child(self)
        new_parent.add_child(self, idx + (1 if direction.offset == 1 else 0))
        return True

    def move_up(self):
        return self.move(Direction.UP)

    def move_down(self):
        return self.move(Direction.DOWN)

    def move_right(self):
        return self.move(Direction.RIGHT)

    def move_left(self):
        return self.move(Direction.LEFT)

    def _move_and_integrate(self, direction):
        old_parent = self.parent
        self.move(direction)
        if self.parent is not old_parent:
            self.integrate(direction)

    def integrate(self, direction):
        if direction.orient != self.parent.orient:
            self._move_and_integrate(direction)
            return
        target_idx = self.index + direction.offset
        if target_idx < 0 or target_idx >= len(self.parent):
            self._move_and_integrate(direction)
            return
        self.reset_size()
        target = self.parent[target_idx]
        self.parent.remove_child(self)
        if target.is_leaf:
            target.flip_with(self)
        else:
            target.add_child(self)

    def integrate_up(self):
        self.integrate(Direction.UP)

    def integrate_down(self):
        self.integrate(Direction.DOWN)

    def integrate_left(self):
        self.integrate(Direction.LEFT)

    def integrate_right(self):
        self.integrate(Direction.RIGHT)

    def find_payload(self, payload):
        if self.payload is payload:
            return self
        for child in self:
            needle = child.find_payload(payload)
            if needle is not None:
                return needle
        return None


class Plasma(Layout):
    """
    A flexible tree-based layout.

    Each tree node represents a container whose children are aligned either
    horizontally or vertically. Each window is attached to a leaf of the tree
    and takes either a calculated relative amount or a custom absolute amount
    of space in its parent container. Windows can be resized, rearranged and
    integrated into other containers.

    Windows in a container will all open in the same direction. Calling
    ``lazy.layout.mode_vertical/horizontal()`` will insert a new container allowing
    windows to be added in the new direction.

    You can use the ``Plasma`` widget to show which mode will apply when opening a new
    window based on the currently focused node.

    Windows can be focused selectively by using ``lazy.layout.up/down/left/right()`` to focus
    the nearest window in that direction relative to the currently focused window.

    "Integrating" windows is best explained with an illustation. Starting with three
    windows, a, b, c. b is currently focused. Calling ``lazy.layout.integrate_left()``
    will have the following effect:

    ::

        ----------------------         ----------------------
        | a    | b    | c    |         | a        | c       |
        |      |      |      |         |          |         |
        |      |      |      |  -->    |          |         |
        |      |      |      |         |----------|         |
        |      |      |      |         | b        |         |
        |      |      |      |         |          |         |
        |      |      |      |         |          |         |
        ----------------------         ----------------------

    Finally, windows can me moved around the layout with ``lazy.layout.move_up/down/left/right()``.

    Example keybindings:

    .. code:: python

        from libqtile.config import EzKey
        from libqtile.lazy import lazy
        ...
        keymap = {
            'M-h': lazy.layout.left(),
            'M-j': lazy.layout.down(),
            'M-k': lazy.layout.up(),
            'M-l': lazy.layout.right(),
            'M-S-h': lazy.layout.move_left(),
            'M-S-j': lazy.layout.move_down(),
            'M-S-k': lazy.layout.move_up(),
            'M-S-l': lazy.layout.move_right(),
            'M-A-h': lazy.layout.integrate_left(),
            'M-A-j': lazy.layout.integrate_down(),
            'M-A-k': lazy.layout.integrate_up(),
            'M-A-l': lazy.layout.integrate_right(),
            'M-d': lazy.layout.mode_horizontal(),
            'M-v': lazy.layout.mode_vertical(),
            'M-S-d': lazy.layout.mode_horizontal_split(),
            'M-S-v': lazy.layout.mode_vertical_split(),
            'M-a': lazy.layout.grow_width(30),
            'M-x': lazy.layout.grow_width(-30),
            'M-S-a': lazy.layout.grow_height(30),
            'M-S-x': lazy.layout.grow_height(-30),
            'M-C-5': lazy.layout.size(500),
            'M-C-8': lazy.layout.size(800),
            'M-n': lazy.layout.reset_size(),
        }
        keys = [EzKey(k, v) for k, v in keymap.items()]

    Acknowledgements:
    This layout was developed by numirias and published at
    https://github.com/numirias/qtile-plasma A few minor amendments have been made
    to that layout as part of incorporating this into the main qtile codebase but the
    majority of the work is theirs.

    """

    defaults = [
        ("name", "Plasma", "Layout name"),
        ("border_normal", "#333333", "Unfocused window border color"),
        ("border_focus", "#00e891", "Focused window border color"),
        ("border_normal_fixed", "#333333", "Unfocused fixed-size window border color"),
        ("border_focus_fixed", "#00e8dc", "Focused fixed-size window border color"),
        ("border_width", 1, "Border width"),
        ("border_width_single", 0, "Border width for single window"),
        ("margin", 0, "Layout margin"),
        (
            "fair",
            False,
            "When ``False`` effort will be made to preserve nodes with a fixed size. "
            "Set to ``True`` to enable new windows to take more space from fixed size nodes.",
        ),
    ]
    # If windows are added before configure() was called, the screen size is
    # still unknown, so we need to set some arbitrary initial root dimensions
    default_dimensions = (0, 0, 1000, 1000)

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Plasma.defaults)
        self.root = Node(None, *self.default_dimensions)
        self._focused = None
        self._add_mode = None
        Node.priority = Priority.BALANCED if self.fair else Priority.FIXED

    def swap(self, c1: Window, c2: Window) -> None:
        node_c1 = node_c2 = None
        for leaf in self.root.all_leafs:
            if leaf.payload is not None:
                if c1 == leaf.payload:
                    node_c1 = leaf
                elif c2 == leaf.payload:
                    node_c2 = leaf
            if node_c1 is not None and node_c2 is not None:
                node_c1.payload, node_c2.payload = node_c2.payload, node_c1.payload
                self.group.layout_all()
                self.group.focus(c1)
                return

    @staticmethod
    def convert_names(tree):
        return [Plasma.convert_names(n) if isinstance(n, list) else n.payload.name for n in tree]

    @property
    def add_mode(self):
        if self._add_mode is None:
            node = self.root_or_focused_node
            if node.width >= node.height:
                return AddMode.HORIZONTAL
            else:
                return AddMode.VERTICAL

        return self._add_mode

    @add_mode.setter
    def add_mode(self, value):
        self._add_mode = value
        # We trigger a redraw so that the different borders can be drawn based on the add_mode
        # We check self._group to avoid raising a runtime error from libqtile.layout.base
        if self._group is not None:
            hook.fire("plasma_add_mode", self)
            self.group.layout_all()

    @property
    def focused(self):
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value
        hook.fire("plasma_add_mode", self)

    @property
    def focused_node(self):
        return self.root.find_payload(self.focused)

    @property
    def root_or_focused_node(self):
        return self.root if self.focused_node is None else self.focused_node

    @property
    def horizontal(self):
        if self.focused_node is None:
            return True

        if self.add_mode is not None:
            if self.add_mode & AddMode.HORIZONTAL:
                return True
            else:
                return False

        if self.focused_node.parent is None:
            if self.focused_node.orient is Orient.HORIZONTAL:
                return True
            else:
                return False

        return self.focused_node.parent.horizontal

    @property
    def vertical(self):
        return not self.horizontal

    @property
    def split(self):
        if self.add_mode is not None and self.add_mode & AddMode.SPLIT:
            return True

        return False

    @expose_command
    def info(self):
        info = super().info()
        tree = self.convert_names(self.root.tree)
        info["tree"] = tree
        info["clients"] = flatten(tree)

        return info

    def clone(self, group):
        clone = copy.copy(self)
        clone._group = group
        clone.root = Node(None, *self.default_dimensions)
        clone.focused = None
        clone.add_mode = None
        return clone

    def get_windows(self):
        clients = []
        for leaf in self.root.all_leafs:
            if leaf.payload is not None:
                clients.append(leaf.payload)
        return clients

    def add_client(self, client):
        new = Node(client)
        try:
            self.root.restore(new)
        except NotRestorableError:
            self.root_or_focused_node.add_node(new, self.add_mode)
        self.add_mode = None

    def remove(self, client):
        self.root.find_payload(client).remove()

    def configure(self, client, screen_rect):
        self.root.x = screen_rect.x
        self.root.y = screen_rect.y
        self.root.width = screen_rect.width
        self.root.height = screen_rect.height
        node = self.root.find_payload(client)
        border_width = self.border_width_single if self.root.tree == [node] else self.border_width
        border_color = getattr(
            self,
            "border_"
            + ("focus" if client.has_focus else "normal")
            + ("" if node.flexible else "_fixed"),
        )
        x, y, width, height = node.pixel_perfect
        client.place(
            x,
            y,
            width - 2 * border_width,
            height - 2 * border_width,
            border_width,
            border_color,
            margin=self.margin,
        )
        # Always keep tiles below floating windows
        client.unhide()

    def focus(self, client):
        self.focused = client
        self.root.find_payload(client).access()

    def focus_first(self):
        return self.root.first_leaf.payload

    def focus_last(self):
        return self.root.last_leaf.payload

    def focus_next(self, win):
        next_leaf = self.root.find_payload(win).next_leaf
        return None if next_leaf is self.root.first_leaf else next_leaf.payload

    def focus_previous(self, win):
        prev_leaf = self.root.find_payload(win).prev_leaf
        return None if prev_leaf is self.root.last_leaf else prev_leaf.payload

    def focus_node(self, node):
        if node is None:
            return
        self.group.focus(node.payload)

    def refocus(self):
        self.group.focus(self.focused)

    @expose_command
    def next(self):
        """Focus next window."""
        self.focus_node(self.focused_node.next_leaf)

    @expose_command
    def previous(self):
        """Focus previous window."""
        self.focus_node(self.focused_node.prev_leaf)

    @expose_command
    def recent(self):
        """Focus most recently focused window.

        (Toggles between the two latest active windows.)
        """
        nodes = [n for n in self.root.all_leafs if n is not self.focused_node]
        most_recent = max(nodes, key=lambda n: n.last_accessed)
        self.focus_node(most_recent)

    @expose_command
    def left(self):
        """Focus window to the left."""
        self.focus_node(self.focused_node.close_left)

    @expose_command
    def right(self):
        """Focus window to the right."""
        self.focus_node(self.focused_node.close_right)

    @expose_command
    def up(self):
        """Focus window above."""
        self.focus_node(self.focused_node.close_up)

    @expose_command
    def down(self):
        """Focus window below."""
        self.focus_node(self.focused_node.close_down)

    @expose_command
    def move_left(self):
        """Move current window left."""
        self.focused_node.move_left()
        self.refocus()

    @expose_command
    def move_right(self):
        """Move current window right."""
        self.focused_node.move_right()
        self.refocus()

    @expose_command
    def move_up(self):
        """Move current window up."""
        self.focused_node.move_up()
        self.refocus()

    @expose_command
    def move_down(self):
        """Move current window down."""
        self.focused_node.move_down()
        self.refocus()

    @expose_command
    def integrate_left(self):
        """Integrate current window left."""
        self.focused_node.integrate_left()
        self.refocus()

    @expose_command
    def integrate_right(self):
        """Integrate current window right."""
        self.focused_node.integrate_right()
        self.refocus()

    @expose_command
    def integrate_up(self):
        """Integrate current window up."""
        self.focused_node.integrate_up()
        self.refocus()

    @expose_command
    def integrate_down(self):
        """Integrate current window down."""
        self.focused_node.integrate_down()
        self.refocus()

    @expose_command
    def mode_horizontal(self):
        """Next window will be added horizontally."""
        self.add_mode = AddMode.HORIZONTAL

    @expose_command
    def mode_vertical(self):
        """Next window will be added vertically."""
        self.add_mode = AddMode.VERTICAL

    @expose_command
    def mode_horizontal_split(self):
        """Next window will be added horizontally, splitting space of current
        window.
        """
        self.add_mode = AddMode.HORIZONTAL | AddMode.SPLIT

    @expose_command
    def mode_vertical_split(self):
        """Next window will be added vertically, splitting space of current
        window.
        """
        self.add_mode = AddMode.VERTICAL | AddMode.SPLIT

    @expose_command
    def set_size(self, x: int):
        """Change size of current window.

        (It's recommended to use `width()`/`height()` instead.)
        """
        self.focused_node.size = x
        self.refocus()

    @expose_command
    def set_width(self, x: int):
        """Set width of current window."""
        self.focused_node.width = x
        self.refocus()

    @expose_command
    def set_height(self, x: int):
        """Set height of current window."""
        self.focused_node.height = x
        self.refocus()

    @expose_command
    def reset_size(self):
        """Reset size of current window to automatic (relative) sizing."""
        self.focused_node.reset_size()
        self.refocus()

    @expose_command
    def grow(self, x: int):
        """Grow size of current window.

        (It's recommended to use `grow_width()`/`grow_height()` instead.)
        """
        self.focused_node.size += x
        self.refocus()

    @expose_command
    def grow_width(self, x: int):
        """Grow width of current window."""
        self.focused_node.width += x
        self.refocus()

    @expose_command
    def grow_height(self, x: int):
        """Grow height of current window."""
        self.focused_node.height += x
        self.refocus()
