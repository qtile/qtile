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
import time
from collections import defaultdict

import pytest
from pytest import approx

from libqtile.config import Screen
from libqtile.confreader import Config
from libqtile.layout.plasma import AddMode, Node, NotRestorableError, Orient, Plasma, Priority
from test.layouts.layout_utils import assert_focused

Node.min_size_default = 10


class Canvas:
    horizontal_line = "\u2500"
    vertical_line = "\u2502"
    tl_corner = "\u250c"
    tr_corner = "\u2510"
    bl_corner = "\u2514"
    br_corner = "\u2518"

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.canvas = defaultdict(lambda: defaultdict(lambda: "#"))

    def add_box(self, x, y, width, height, name="*"):
        width = width - 1
        height = height - 1
        label = str(name)[: width - 1]
        for i in range(x, width + x):
            self.canvas[i][y] = self.horizontal_line
            self.canvas[i][y + height] = self.horizontal_line
        for i in range(y, height + y):
            self.canvas[x][i] = self.vertical_line
            self.canvas[x + width][i] = self.vertical_line
        for i in range(x + 1, width + x):
            for j in range(y + 1, y + height):
                self.canvas[i][j] = "."
        for i, char in enumerate(label):
            self.canvas[x + 1 + i][y + 1] = char
        self.canvas[x][y] = self.tl_corner
        self.canvas[x + width][y] = self.tr_corner
        self.canvas[x][y + height] = self.bl_corner
        self.canvas[x + width][y + height] = self.br_corner

    def view(self):
        res = ""
        for y in range(self.height):
            for x in range(self.width):
                res += self.canvas[x][y]
            res += "\n"
        return res


def tree(node, level=0):
    res = "{indent}{name} {orient} {repr_} {pos} {size} {parent}\n".format(
        indent=level * 4 * " ",
        name="%s" % (node.payload or "*"),
        orient="H" if node.horizontal else "V",
        repr_=f"{repr(node)}",
        pos=f"{node.width:g}*{node.height:g}@{node.x:g}:{node.y:g}",
        size="size: {}{}".format(node.size, " (auto)" if node.flexible else ""),
        parent=f"p: {node.parent}",
    )
    for child in node:
        res += tree(child, level + 1)
    return res


def draw(root):
    canvas = Canvas(root.width, root.height)

    def add(node):
        if node.is_leaf:
            canvas.add_box(*node.pixel_perfect, node.payload)
        for child in node:
            add(child)

    add(root)
    return canvas.view()


def info(node):
    print(tree(node))
    print(draw(node))


def create_nodes(string):
    for x in string.split():
        yield Node(x)


@pytest.fixture
def root():
    root = Node("root", 0, 0, 120, 50)
    return root


@pytest.fixture
def tiny_grid(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    return a, b, c


@pytest.fixture
def small_grid(root):
    a, b, c, d = create_nodes("a b c d")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    c.flip_with(d)
    return a, b, c, d


@pytest.fixture
def grid(root):
    a, b, c, d, e = create_nodes("a b c d e")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    c.flip_with(d)
    c.parent.add_child(e)
    return a, b, c, d, e


@pytest.fixture
def complex_grid(root):
    a, b, c, d, e, f, g = create_nodes("a b c d e f g")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    c.flip_with(d)
    c.parent.add_child(e)
    c.flip_with(f)
    f.flip_with(g)
    return a, b, c, d, e, f, g


@pytest.fixture(autouse=True)
def reset_node_priority():
    yield
    Node.priority = Priority.FIXED


##############
# TEST NODES #
##############


def test_single_node():
    n = Node(None, 0, 0, 120, 50)
    assert n.x == 0
    assert n.y == 0
    assert n.width == 120
    assert n.height == 50
    assert n.is_root is True
    assert n.is_leaf is True
    assert n.parent is None
    assert n.children == []
    assert n.orient == Orient.HORIZONTAL
    assert n.horizontal is True
    assert n.vertical is False
    assert n.size is None
    assert (n.x, n.y) == n.pos


def test_add_child(root):
    """Single child fills the entire root node's space."""
    child = Node("a")
    root.add_child(child)
    assert root.children == [child]
    assert child.parent == root
    assert root.width == child.width == 120
    assert root.height == child.height == 50
    assert root.x == child.x == 0
    assert root.y == child.y == 0


def test_add_children(root):
    """Multiple children will split the root node's space."""
    a, b = create_nodes("a b")
    root.add_child(a)
    root.add_child(b)
    assert root.width == 120
    assert a.width == b.width == 60
    assert root.height == 50
    assert a.height == b.height == 50
    assert a.pos == (0, 0)
    assert b.pos == (60, 0)
    c = Node("c")
    root.add_child(c)
    assert a.width == b.width == c.width == 40
    assert a.pos == (0, 0)
    assert b.pos == (40, 0)
    assert c.pos == (80, 0)


def test_add_child_after(root, grid):
    """Test adding nodes in specific positions."""
    a, b, c, d, e = grid
    f = Node("f")
    g = Node("g")
    h = Node("h")
    # add_child is called on the target node's parent
    # i.e. the node containing the target
    root.add_child_after(f, a)
    assert root.tree == [a, f, [b, [c, d, e]]]
    b.parent.add_child_after(g, b)
    assert root.tree == [a, f, [b, g, [c, d, e]]]
    d.parent.add_child_after(h, d)
    assert root.tree == [a, f, [b, g, [c, d, h, e]]]


def test_add_child_after_with_sizes(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    a.size += 10
    b.size += 10
    b.parent.add_child_after(c, b)
    assert a.size == b.size == 55
    assert c.size == 10


def test_remove_child(root):
    a, b = create_nodes("a b")
    root.add_child(a)
    root.add_child(b)
    root.remove_child(a)
    assert root.children == [b]
    root.remove_child(b)
    assert root.children == []


def test_nested(root):
    a, b, c, d = create_nodes("a b c d")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    assert a.width == 60
    assert b.width == 60
    assert c.width == 60
    assert a.height == 50
    assert b.height == 25
    assert c.height == 25
    b.flip_with(d)
    assert b.width == 30
    assert d.width == 30


def test_leaves(root, grid):
    a, b, c, d, e = grid
    assert root.first_leaf is a
    assert root.last_leaf is e
    assert b.parent.first_leaf is b
    assert b.parent.last_leaf is e


def test_directions(root, grid):
    a, b, c, d, e = grid
    assert a.up is None
    assert a.right is b
    assert a.down is None
    assert a.left is None

    assert b.up is None
    assert b.right is None
    assert b.down is c
    assert b.left is a

    assert c.up is b
    assert c.right is d
    assert c.down is None
    assert c.left is a

    assert d.up is b
    assert d.right is e
    assert d.down is None
    assert d.left is c

    assert e.up is b
    assert e.right is None
    assert e.down is None
    assert e.left is d


def test_prev_next(grid):
    a, b, c, d, e = grid
    assert a.next_leaf == b
    assert b.next_leaf == c
    assert c.next_leaf == d
    assert d.next_leaf == e
    assert e.next_leaf == a
    assert a.prev_leaf == e
    assert e.prev_leaf == d
    assert d.prev_leaf == c
    assert c.prev_leaf == b
    assert b.prev_leaf == a


def test_siblings(grid):
    a, b, c, d, e = grid
    assert d.siblings == [c, e]
    assert b.siblings == [c.parent]


def test_root_siblings(root):
    siblings = root.siblings
    assert siblings == []


def test_move_forward(root, grid):
    a, b, c, d, e = grid
    assert c.parent.children == [c, d, e]
    c.move_right()
    assert c.parent.children == [d, c, e]
    c.move_right()
    assert c.parent.children == [d, e, c]
    c.move_right()
    assert root.tree == [a, [b, [d, e]], c]


def test_move_backward(root, grid):
    a, b, c, d, e = grid
    e.move_left()
    assert c.parent.children == [c, e, d]
    e.move_left()
    assert c.parent.children == [e, c, d]
    e.move_left()
    assert root.tree == [a, e, [b, [c, d]]]


def test_advanced_move(grid):
    a, b, c, d, e = grid
    c.move_up()
    assert b.parent.tree == [b, c, [d, e]]
    a.move_up()
    assert b.parent.tree == [b, c, [d, e]]


def test_advanced_move2(root, grid):
    a, b, c, d, e = grid
    res = c.move_down()
    assert b.parent.tree == [b, [d, e], c]
    assert res is True
    res = e.move_down()
    assert b.parent.tree == [b, d, e, c]
    assert res is True
    res = e.move_left()
    assert root.tree == [a, e, [b, d, c]]
    assert res is True
    res = d.move_right()
    assert root.tree == [a, e, [b, c], d]
    assert res is True
    res = a.move_left()
    assert root.tree == [a, e, [b, c], d]
    assert res is False
    res = d.move_right()
    assert root.tree == [a, e, [b, c], d]
    assert res is False


def test_move_blocked(root, grid):
    a, b, c, d, e = grid
    orig_tree = root.tree.copy()
    res = a.move_up()
    assert root.tree == orig_tree
    assert res is False
    res = b.move_up()
    assert root.tree == orig_tree
    assert res is False


def test_move_root(root):
    a = Node("a")
    root.add_child(a)
    root.move_up()
    assert root.tree == [a]


def test_integrate(root):
    a, b, c, d, e = create_nodes("a b c d e")
    root.add_child(a)
    root.add_child(b)
    root.add_child(c)
    root.add_child(d)
    c.integrate_left()
    assert root.tree == [a, [b, c], d]
    a.integrate_right()
    assert root.tree == [[b, c, a], d]
    a.parent.add_child(e)
    c.integrate_down()
    assert root.tree == [[b, [a, c], e], d]
    e.integrate_up()
    assert root.tree == [[b, [a, c, e]], d]


def test_integrate_nested(root, grid):
    a, b, c, d, e = grid
    c.integrate_right()
    assert root.tree == [a, [b, [[d, c], e]]]


def test_move_and_integrate(root, grid):
    a, b, c, d, e = grid
    c.integrate_left()
    assert root.tree == [[a, c], [b, [d, e]]]
    a.integrate_right()
    assert root.tree == [c, [b, [d, e], a]]
    d.integrate_down()
    assert root.tree == [c, [b, e, [a, d]]]
    a.integrate_up()
    assert root.tree == [c, [b, [e, a], d]]
    e.integrate_left()
    assert root.tree == [[c, e], [b, a, d]]
    f = Node("f")
    a.flip_with(f)
    g = Node("g")
    a.flip_with(g)
    g.integrate_left()
    assert root.tree == [[c, e, g], [b, [a, f], d]]


def test_impossible_integrate(root, grid):
    a, b, c, d, e = grid
    orig_tree = root.tree.copy()
    a.integrate_left()
    assert orig_tree == root.tree
    b.integrate_up()
    assert orig_tree == root.tree


def test_impossible_integrate2(root):
    a, b = create_nodes("a b")
    root.add_child(a)
    root.add_child(b)
    orig_tree = root.tree.copy()
    b.integrate_up()
    assert root.tree == orig_tree
    b.integrate_down()
    assert root.tree == orig_tree
    b.integrate_right()
    assert root.tree == orig_tree
    a.integrate_up()
    assert root.tree == orig_tree
    a.integrate_down()
    assert root.tree == orig_tree
    a.integrate_left()
    assert root.tree == orig_tree


def test_find_payload(root, grid):
    a, b, c, d, e = grid
    assert root.find_payload(a.payload) is a
    assert root.find_payload(b.payload) is b
    assert root.find_payload(d.payload) is d
    assert root.find_payload("x") is None


def test_last_access(grid):
    a, b, c, d, e = grid
    f = Node("f")
    a.flip_with(f)
    d.access()
    assert b.down is d
    b.access()
    assert f.right is b
    f.access()
    assert b.left is f


def test_root_without_dimensions():
    """A root node with undef. dimensions should be able to add a child."""
    root = Node()
    x = Node("x")
    root.add_child(x)


def test_root(root, grid):
    for node in grid:
        assert node.root is root


def test_all(root, grid):
    assert set(root.all_leafs) == set(grid)


def test_close_neighbor(root):
    a, b, c, d = create_nodes("a b c d")
    root.add_child(a)
    root.add_child(b)
    a.flip_with(c)
    b.flip_with(d)
    assert a.close_up is None
    assert a.close_left is None
    assert a.close_right is b
    assert a.close_down is c

    assert b.close_up is None
    assert b.close_left is a
    assert b.close_right is None
    assert b.close_down is d

    assert c.close_up is a
    assert c.close_left is None
    assert c.close_right is d
    assert c.close_down is None

    assert d.close_up is b
    assert d.close_left is c
    assert d.close_right is None
    assert d.close_down is None


def test_close_neighbor2(root, small_grid):
    a, b, c, d = small_grid
    assert b.close_left is a


def test_close_neighbor_nested(root, grid):
    a, b, c, d, e = grid
    f, g, h, i, j, k, m = create_nodes("f g h i j k m")
    root.add_child(f)
    d.flip_with(h)
    a.flip_with(i)
    e.flip_with(j)
    e.parent.add_child(k)
    f.flip_with(m)
    f.height = 10
    assert b.close_down is d
    b.flip_with(g)
    assert b.close_down is c
    assert d.close_right is e
    assert e.close_left is d
    assert m.close_left is e
    assert e.close_up is g
    assert m.close_right is None
    assert h.close_down is None


def test_close_neighbor_approx(root, small_grid):
    """Tolerate floating point errors when calculating common borders."""
    root.height += 30
    a, b, c, d = small_grid
    e, f, g = create_nodes("e f g")
    c.flip_with(f)
    b.parent.add_child(e)
    c.parent.add_child(g)
    assert g.close_down is e


def test_points(root, small_grid):
    a, b, c, d = small_grid
    assert c.x, c.y == (60, 25)
    assert c.x + c.width, c.y == (90, 25)
    assert c.x, c.y + c.height == (60, 50)
    assert c.x + c.width, c.y + c.height == (90, 50)


def test_center(root):
    assert root.x_center == 60
    assert root.y_center == 25
    assert root.center == (60, 25)


def test_recent_leaf(root, grid):
    a, b, c, d, e = grid
    assert d.parent.recent_leaf is c
    c.access()
    d.access()
    assert d.parent.recent_leaf is d
    b.access()
    c.access()
    assert root.recent_leaf is c
    a.access()
    assert root.recent_leaf is a


def test_recent_close_neighbor(root, grid):
    a, b, c, d, e = grid
    assert b.close_down is d
    c.access()
    assert b.close_down is c
    assert a.close_right is c
    b.access()
    assert a.close_right is b


def test_add_node(root):
    a, b, c, d, e, f, g = create_nodes("a b c d e f g")
    root.add_node(a)
    assert root.tree == [a]
    root.add_node(b)
    assert root.tree == [a, b]
    a.add_node(c)
    assert root.tree == [a, c, b]
    c.add_node(d, mode=AddMode.HORIZONTAL)
    assert root.tree == [a, c, d, b]
    root.remove_child(d)
    c.add_node(d, mode=AddMode.VERTICAL)
    c.parent.add_child_after
    assert root.tree == [a, [c, d], b]
    c.add_node(e, mode=AddMode.VERTICAL)
    assert root.tree == [a, [c, e, d], b]
    assert a.width == 40
    a.add_node(f, mode=AddMode.HORIZONTAL | AddMode.SPLIT)
    assert root.tree == [a, f, [c, e, d], b]
    assert a.width == f.width == 20
    assert c.parent.width == b.width == 40
    a.add_node(g, mode=AddMode.VERTICAL | AddMode.SPLIT)
    assert root.tree == [[a, g], f, [c, e, d], b]


def test_contains(root, grid):
    x = Node("x")
    nodes = list(grid)
    nodes += [n.parent for n in nodes]
    nodes.append(root)
    for n in nodes:
        assert n in root
    assert x not in root


def test_size(grid):
    a, b, c, d, e = grid
    assert a.size == a.width == 60
    assert b.size == b.height == 25


def test_capacity(root, grid):
    a, b, c, d, e = grid
    assert root.capacity == 120
    assert b.parent.capacity == 50
    assert c.parent.capacity == 60
    assert c.capacity == 25


def test_capacity2(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)


def test_resize(root, grid):
    a, b, c, d, e = grid
    a.size += 10
    assert a.width == a.size == 70
    assert b.height == b.size == 25
    assert b.width == 50
    assert c.width == d.width == e.width == 50 / 3
    assert a.pos == (0, 0)
    assert b.pos == (70, 0)
    assert c.pos == (70, 25)
    assert d.pos == (70 + 50 / 3, 25)
    assert e.pos == (70 + (50 / 3) * 2, 25)
    b.size -= 5
    assert c.width == d.width == e.width == 50 / 3
    assert c.height == d.height == e.height == 30
    d.size += 5
    assert d.width == 50 / 3 + 5
    d.move_up()
    assert d.size == (50 - b.size) / 2
    b.integrate_down()
    assert b.size == d.size == 25
    assert b.parent.size == 25


def test_resize_absolute(grid):
    a, b, c, d, e = grid
    b.size = 10
    assert b.size == b.height == 10
    assert c.parent.size == 40
    b.size = 5
    assert b.size == 10


def test_resize_absolute2(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    root.add_child(c)
    a.size = 30
    b.size = 60
    c.size = 40
    assert a.size == 30 * (80 / 90)
    assert b.size == 60 * (80 / 90)
    assert c.size == 40


def test_resize_absolute_and_relative(root):
    a, b, c, d = create_nodes("a b c d")
    root.add_child(a)
    root.add_child(b)
    a.size = 20
    b.size = 20
    assert a.size == 100
    assert b.size == 20
    root.add_child(c)
    assert c.size == approx(10)
    assert a.size == approx(100 * (11 / 12))
    assert b.size == approx(20 * (11 / 12))
    root.add_child(d)
    assert c.size == d.size == approx(10)


def test_resize_absolute_and_relative_balanced(root):
    Node.priority = Priority.BALANCED
    a, b, c, d = create_nodes("a b c d")
    root.add_child(a)
    root.add_child(b)
    a.size = 20
    b.size = 20
    assert a.size == 100
    assert b.size == 20
    root.add_child(c)
    assert c.size == approx(40)
    assert a.size == approx(100 * (2 / 3))
    assert b.size == approx(20 * (2 / 3))
    root.add_child(d)
    assert c.size == d.size == approx(20)


def test_resize_absolute_and_relative2(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    root.add_child(c)
    a.size += 10
    assert a.size == 50
    assert b.size == 35
    assert c.size == 35
    b.size += 10
    assert a.size == 50
    assert b.size == 45
    assert c.size == 25


def test_resize_flat(root):
    a, b, c, d, e, f = create_nodes("a b_abs c d e_abs f_abs")
    root.add_child(a)
    root.add_child(b)
    root.add_child(c)
    root.add_child(d)
    d.flip_with(e)
    e.flip_with(f)
    b.size = b.size
    e.size = e.size
    f.size = f.size
    a.size = 60
    assert a.size == 60
    assert b.size == 25
    assert c.size == 10
    assert d.parent.size == 25
    assert e.size == f.size == 25 / 2


def test_resize_minimum(grid):
    a, b, c, d, e = grid
    b.size -= 100
    assert b.size == 10


def test_resize_all_absolute_underflow(root, grid):
    a, b, c, d, e = grid
    c.size = 10
    d.size = 10
    assert e.size == 40
    e.size = 10
    assert e.size == 10
    assert c.size == d.size == 25


def test_resize_all_absolute_overflow(grid):
    a, b, c, d, e = grid
    c.size = d.size = 15
    e.size = 40
    assert e.size == 40
    assert c.size == d.size == 10
    e.size = 50
    assert e.size == 40
    assert c.size == d.size == 10


def test_resize_overflow_with_relative(root, grid):
    a, b, c, d, e = grid
    c.size = 20
    d.size = 40
    assert c.size == 10
    assert d.size == 40
    assert e.size == 10
    assert e.flexible
    d.size = 50
    assert c.size == 10
    assert d.size == 40
    assert e.size == 10
    assert e.flexible


def test_resize_overflow_with_relative2(root, grid):
    a, b, c, d, e = grid
    c.size = 20
    d.size = 20
    a.size = 70
    assert a.size == 70
    assert c.size == d.size == 20
    assert e.size == 10
    a.size = 80
    assert a.size == 80
    assert c.size == d.size == 15
    assert e.size == 10
    a.size = 90
    assert a.size == 90
    assert c.size == d.size == e.size == 10
    a.size = 100
    assert a.size == 90


def test_resize_only_absolute_remains(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    a.size = 20
    b.size = 20
    root.add_child(c)
    root.remove_child(c)
    assert a.size == 100
    assert b.size == 20


def test_reset_size(grid):
    a, b, c, d, e = grid
    a.size += 5
    assert a.size == 65
    a.reset_size()
    assert a.size == 60


def test_size_after_split(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    b.size -= 20
    b.flip_with(c)
    assert b.parent.size == 40
    assert b.size == c.size == 25
    b.remove()
    assert c.size == 40


def test_only_child_must_be_flexible(root):
    a, b = create_nodes("a b")
    root.add_child(a)
    root.add_child(b)
    a.size = 10
    root.remove_child(b)
    assert a.flexible


def test_deny_only_child_resize(root):
    a = Node("a")
    root.add_child(a)
    a.size = 10
    assert a.size == 120


def test_resize_parents(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    b.width += 10
    assert b.parent.size == 70
    assert b.size == c.size == 25


def test_pixelperfect(root, tiny_grid):
    a, b, c = tiny_grid
    root._height = 11
    root._width = 11
    ds = a.pixel_perfect
    assert all(type(x) is int for x in (ds.x, ds.y, ds.width, ds.height))
    assert a.width + b.width == 11
    assert a.pixel_perfect.width + b.pixel_perfect.width == 11
    assert b.height + c.height == 11
    assert b.pixel_perfect.height + c.pixel_perfect.height == 11


def test_pixelperfect_draw(root, complex_grid):
    root._height = 10
    for i in range(40, 50):
        root._width = i
        view = draw(root)
        assert "#" not in view
    root._width = 50
    for i in range(10, 20):
        root._height = i
        view = draw(root)
        assert "#" not in view


def test_resize_root(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    a.height += 10
    root.height += 10
    root.width += 10
    root.size = 10
    assert a._size is b._size is root._size is None


def test_set_xy(root, tiny_grid):
    a, b, c = tiny_grid
    root.x = 10
    root.y = 20
    assert root.x == 10
    assert root.y == 20
    a.x = 30
    a.y = 40
    assert a.x == root.x == 10
    assert a.y == root.y == 20
    root.width = 50
    root.height = 60
    assert root._width == 50
    assert root._height == 60


def test_set_width_height(root, tiny_grid):
    a, b, c = tiny_grid
    a.width = 70
    assert a.width == 70
    assert b.width == c.width == 50
    b.height = 30
    assert b.height == 30
    assert c.height == 20
    b.width = 80
    assert b.width == c.width == 80
    assert a.width == 40
    a.height = 20
    assert a.height == 50


def test_min_size(root, small_grid):
    a, b, c, d = small_grid
    c.size += 10
    d.size += 20
    b.size = 20
    assert a.min_size == Node.min_size_default
    assert b.parent.min_size == 60
    assert b.min_size == 20
    assert c.parent.min_size == Node.min_size_default
    assert c.min_size == 20
    assert d.min_size == 40


def test_transitive_flexible(root, complex_grid):
    a, b, c, d, e, f, g = complex_grid
    assert b.parent.flexible
    d.size = 20
    e.size = 20
    f.size = 10
    assert b.parent.flexible
    g.size = 10
    assert not b.parent.flexible


def test_resize_bubbles(root, small_grid):
    a, b, c, d = small_grid
    c.size += 10
    d.size += 20
    assert c.size == 20
    assert d.size == 40
    a.size = 30
    assert c.size == 30
    assert d.size == 60


def test_resize_bubbles2(root, complex_grid):
    a, b, c, d, e, f, g = complex_grid
    c.flip_with(Node("h"))
    f.size += 10
    g.size += 10
    assert f.size == g.size == 10
    assert f.fixed and g.fixed
    assert d.size == e.size == 20
    assert d.flexible and e.flexible
    a.size -= 40
    assert a.size == 20
    assert f.size == g.size == 10
    assert d.size == e.size == 40
    d.size = 10
    assert d.size == 10
    assert e.size == 70
    assert f.size == g.size == 10
    assert e.flexible
    e.size = 10
    assert e.fixed


def test_resize_bubbles3(root, complex_grid):
    a, b, c, d, e, f, g = complex_grid
    h = Node("h")
    c.flip_with(h)
    f.size += 10
    g.size += 10
    assert f.size == g.size == c.size == h.size == 10
    a.size = 10
    assert a.size == 10
    assert f.size == g.size == c.size == h.size == 10
    assert d.size == e.size == 45
    d.size = 10
    assert d.size == 10
    assert e.size == 80
    e.size = 10
    assert e.size == 10
    assert f.size == g.size == c.size == h.size == d.size == 100 / 3


def test_resize_nested(root):
    a, b, c, d, e, f, g, h = create_nodes("a b c_abs d_abs e f g h_abs")
    nu1, nu2, nd, mu, md1, md2 = create_nodes("nu1_abs nu2_abs nd mu md1_abs md2")
    ou1, ou2, od, pu, pd1, pd2 = create_nodes("ou1_abs ou2_abs od pu pd1_abs pd2_abs")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    b.parent.add_child(e)
    b.parent.add_child(g)
    c.flip_with(d)
    e.flip_with(f)
    g.flip_with(h)

    b.parent.add_child(nu1)
    nu1.flip_with(mu)
    nu1.flip_with(nd)
    nu1.flip_with(nu2)
    mu.flip_with(md1)
    md1.flip_with(md2)

    b.parent.add_child(ou1)
    ou1.flip_with(pu)
    ou1.flip_with(od)
    ou1.flip_with(ou2)
    pu.flip_with(pd1)
    pd1.flip_with(pd2)

    def assert_first_state():
        assert b.parent.size == 60
        assert c.size == approx(40)
        assert d.size == 20
        assert e.size == f.size == 30
        assert g.size == 40
        assert h.size == 20
        assert nu1.size == 10
        assert nu2.size == 20
        assert nd.parent.size == 30
        assert mu.parent.size == 30
        assert md1.size == 10
        assert md2.size == 20
        assert ou1.size == 10
        assert ou2.size == 20
        assert od.parent.size == 30
        assert pu.parent.size == 30
        assert pd1.size == 10
        assert pd2.size == 20

    def assert_second_state():
        assert a.size == 30
        assert b.parent.size == 90
        assert c.size == 60
        assert d.size == 30
        assert e.size == f.size == 45
        assert g.size == 70
        assert h.size == 20
        assert nu1.size == 10
        assert nu2.size == 20
        assert nd.parent.size == 30
        assert mu.parent.size == 60
        assert md1.size == 10
        assert md2.size == 50
        assert ou1.size == 15
        assert ou2.size == 30
        assert od.parent.size == 45
        assert pd1.size == 15
        assert pd2.size == 30
        assert pu.parent.size == 45

    b.parent.size = 60
    c.size += 5
    d.size -= 5
    h.size = 20
    nu1.size = 10
    nu2.size = 20
    md1.size = 10
    ou1.size = 10
    ou2.size = 20
    pd1.size = 10
    pd2.size = 20

    assert a.size == 60
    assert_first_state()
    a.size -= 30
    assert_second_state()
    a.size += 30
    assert a.size == 60
    assert_first_state()
    b.parent.size += 30
    assert_second_state()
    b.parent.size -= 30
    assert a.size == 60
    assert_first_state()


def test_resize_nested_balanced(root):
    Node.priority = Priority.BALANCED
    a, b, c, d, e, f, g, h = create_nodes("a b c_abs d_abs e f g h_abs")
    nu1, nu2, nd, mu, md1, md2 = create_nodes("nu1_abs nu2_abs nd mu md1_abs md2")
    ou1, ou2, od, pu, pd1, pd2 = create_nodes("ou1_abs ou2_abs od pu pd1_abs pd2_abs")
    root.add_child(a)
    root.add_child(b)
    b.flip_with(c)
    b.parent.add_child(e)
    b.parent.add_child(g)
    c.flip_with(d)
    e.flip_with(f)
    g.flip_with(h)

    b.parent.add_child(nu1)
    nu1.flip_with(mu)
    nu1.flip_with(nd)
    nu1.flip_with(nu2)
    mu.flip_with(md1)
    md1.flip_with(md2)

    b.parent.add_child(ou1)
    ou1.flip_with(pu)
    ou1.flip_with(od)
    ou1.flip_with(ou2)
    pu.flip_with(pd1)
    pd1.flip_with(pd2)

    def assert_first_state():
        assert b.parent.size == 60
        assert c.size == 40
        assert d.size == 20
        assert e.size == f.size == 30
        assert g.size == 40
        assert h.size == 20
        assert nu1.size == 10
        assert nu2.size == 20
        assert nd.parent.size == 30
        assert mu.parent.size == 30
        assert md1.size == 10
        assert md2.size == 20
        assert ou1.size == 10
        assert ou2.size == 20
        assert od.parent.size == 30
        assert pu.parent.size == 30
        assert pd1.size == 10
        assert pd2.size == 20

    def assert_second_state():
        assert a.size == 30
        assert b.parent.size == 90
        assert c.size == 60
        assert d.size == 30
        assert e.size == f.size == 45
        assert g.size == 70
        assert h.size == 20
        assert nu1.size == 10
        assert nu2.size == 20
        assert nd.parent.size == 30
        assert mu.parent.size == 60
        assert md1.size == 10
        assert md2.size == 50
        assert ou1.size == 15
        assert ou2.size == 30
        assert od.parent.size == 45
        assert pd1.size == 15
        assert pd2.size == 30
        assert pu.parent.size == 45

    b.parent.size = 60
    c.size += 5
    d.size -= 5
    h.size = 20
    nu1.size = 10
    nu2.size = 20
    md1.size = 10
    ou1.size = 10
    ou2.size = 20
    pd1.size = 10
    pd2.size = 20

    assert a.size == 60
    assert_first_state()
    a.size -= 30
    assert_second_state()
    a.size += 30
    assert a.size == 60
    assert_first_state()
    b.parent.size += 30
    assert_second_state()
    b.parent.size -= 30
    assert a.size == 60
    assert_first_state()

    a.size = 30
    x = Node("x")
    root.add_child(x)
    assert x.size == 40
    assert_first_state()
    x.remove()
    assert_second_state()

    a.remove()
    assert b.width == 120
    y = Node("y")
    root.add_child(y)
    assert_first_state()


def test_resize_max(root, tiny_grid):
    a, b, c = tiny_grid
    a.width = 120
    assert a.width == 110
    assert b.width == c.width == 10


def test_restore(root, grid):
    a, b, c, d, e = grid
    tree = root.tree
    for node in grid:
        node.remove()
        root.restore(node)
        assert root.tree == tree


def test_restore_same_payload(root, grid):
    """Restore a node that's not identical with the removed one but carries
    the same payload.
    """
    a, b, c, d, e = grid
    d.remove()
    new_d = Node("d")
    root.restore(new_d)
    assert root.tree == [a, [b, [c, new_d, e]]]


def test_restore_unknown(root, grid):
    a, b, c, d, e = grid
    with pytest.raises(NotRestorableError):
        root.restore(Node("x"))
    d.remove()
    with pytest.raises(NotRestorableError):
        root.restore(Node("x"))
    root.restore(d)
    assert root.tree == [a, [b, [c, d, e]]]


def test_restore_no_parent(root, small_grid):
    a, b, c, d = small_grid
    c.remove()
    d.remove()
    with pytest.raises(NotRestorableError):
        root.restore(c)
    root.restore(d)
    assert root.tree == [a, [b, d]]


def test_restore_bad_index(root, grid):
    a, b, c, d, e = grid
    f, g = create_nodes("f g")
    e.parent.add_child(f)
    e.parent.add_child(g)
    g.remove()
    f.remove()
    e.remove()
    root.restore(g)
    assert root.tree == [a, [b, [c, d, g]]]


def test_restore_sizes(root, grid):
    a, b, c, d, e = grid
    c.size = 30
    c.remove()
    root.restore(c)
    assert c.size == 30
    c.remove()
    d.size = 30
    e.size = 30
    assert d.size == e.size == 30
    root.restore(c)
    assert c.size == 30
    assert d.size == e.size == 15


def test_restore_sizes_flip(root, tiny_grid):
    a, b, c = tiny_grid
    c.size = 10
    c.remove()
    assert a._size is b._size is None
    root.restore(c)
    assert c.size == 10
    b.size = 10
    c.remove()
    root.restore(c)
    assert b.size == 10
    b.remove()
    root.restore(b)
    assert b.size == 10


def test_restore_root(root):
    a, b = create_nodes("a b")
    root.add_child(a)
    root.add_child(b)
    a.size = 20
    a.remove()
    root.restore(a)
    assert a._size == 20
    assert b._size is None
    b.remove()
    root.restore(b)
    assert a._size == 20
    assert b._size is None


def test_restore_root2(root):
    a, b, c = create_nodes("a b c")
    root.add_child(a)
    root.add_child(b)
    root.add_child(c)
    b.size = 20
    c.size = 40
    a.remove()
    assert b.size == 40
    assert c.size == 80
    root.restore(a)
    assert not a.fixed
    assert a.size == approx(60)
    assert b.size == approx(20)
    assert c.size == approx(40)


def test_restore_keep_flexible(root, tiny_grid):
    a, b, c = tiny_grid
    b.remove()
    root.restore(b)
    assert a._size is b._size is c._size is None
    b.size = 10
    b.remove()
    root.restore(b)
    assert b._size == 10
    assert c._size is None
    c.remove()
    root.restore(c)
    assert b._size == 10
    assert c._size is None
    c.size = 10
    b.reset_size()
    b.remove()
    root.restore(b)
    assert b._size is None
    assert c._size == 10
    c.remove()
    root.restore(c)
    assert b._size is None
    assert c._size == 10


def test_resize_with_collapse_and_restore(root, small_grid):
    a, b, c, d = small_grid
    root.height = 30
    c.size = 30
    d.size += 10
    b.remove()
    assert c.size == c.height == 10
    assert d.size == d.height == 20
    root.restore(b)
    assert b.height == 15
    assert b.width == 60
    assert c.height == d.height == 15
    assert c.width == 20
    assert d.width == 40


def test_node_repr(root, grid):
    a, b, c, d, e = grid
    assert repr(root).startswith("<Node root +2 ")
    assert repr(a).startswith("<Node a ")
    assert repr(b).startswith("<Node b ")
    assert repr(c).startswith("<Node c ")
    assert repr(d).startswith("<Node d ")
    assert repr(e).startswith("<Node e ")


################
# LAYOUT TESTS #
################


@pytest.fixture
def load_grid(request):
    return getattr(request, "param", False)


@pytest.fixture
def plasma(manager_nospawn, request, load_grid):
    class PlasmaConfig(Config):
        layouts = [Plasma(**getattr(request, "param", dict()))]
        screens = [Screen()]

    manager_nospawn.start(PlasmaConfig)

    if load_grid:
        manager_nospawn.test_window("a")
        manager_nospawn.test_window("b")
        manager_nospawn.c.layout.previous()
        manager_nospawn.c.layout.mode_vertical()
        manager_nospawn.test_window("c")
        manager_nospawn.c.layout.right()
        manager_nospawn.c.layout.mode_vertical()
        manager_nospawn.test_window("d")

    yield manager_nospawn


def config(**kwargs):
    return pytest.mark.parametrize("plasma", [kwargs], indirect=True)


with_grid = pytest.mark.parametrize("load_grid", [True], indirect=True)


class Client:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def client_tree(plasma):
    return plasma.c.layout.info()["tree"]


def test_init():
    layout = Plasma()
    assert isinstance(layout.root, Node)


def test_focus(root):
    layout = Plasma()
    layout.root = root
    a, b, c, d = (Client(x) for x in "abcd")
    layout.add_client(a)
    layout.add_client(b)
    layout.add_client(c)
    layout.add_client(d)
    assert layout.focus_first() is a
    assert layout.focus_last() is d
    assert layout.focus_next(b) is c
    assert layout.focus_previous(c) is b
    layout.focus(c)
    assert layout.focused is c


def test_access(root):
    layout = Plasma()
    layout.root = root
    layout.add_client("a")
    now = time.time()
    assert layout.root.find_payload("a").last_accessed < now
    layout.focus("a")
    assert layout.root.find_payload("a").last_accessed > now


def test_info(plasma):
    plasma.test_window("a")
    plasma.test_window("b")
    assert client_tree(plasma) == ["a", "b"]


def test_windows(plasma):
    plasma.test_window("a")
    plasma.test_window("b")
    plasma.test_window("c")
    assert_focused(plasma, "c")
    assert client_tree(plasma) == ["a", ["b", "c"]]


def test_split_directions(plasma):
    plasma.test_window("a")
    plasma.c.layout.mode_horizontal()
    plasma.test_window("b")
    plasma.c.layout.mode_vertical()
    plasma.test_window("c")
    assert client_tree(plasma) == ["a", ["b", "c"]]


@with_grid
def test_layout_directions(plasma):
    assert_focused(plasma, "d")
    plasma.c.layout.left()
    assert_focused(plasma, "c")
    plasma.c.layout.up()
    assert_focused(plasma, "a")
    plasma.c.layout.right()
    assert_focused(plasma, "b")
    plasma.c.layout.down()
    assert_focused(plasma, "d")
    plasma.c.layout.down()
    assert_focused(plasma, "d")
    plasma.c.layout.previous()
    assert_focused(plasma, "b")
    plasma.c.layout.next()
    assert_focused(plasma, "d")


@with_grid
def test_move(plasma):
    assert client_tree(plasma) == [["a", "c"], ["b", "d"]]
    plasma.c.layout.move_up()
    assert client_tree(plasma) == [["a", "c"], ["d", "b"]]
    plasma.c.layout.move_down()
    assert client_tree(plasma) == [["a", "c"], ["b", "d"]]
    plasma.c.layout.move_left()
    assert client_tree(plasma) == [["a", "c"], "d", "b"]
    plasma.c.layout.move_right()
    assert client_tree(plasma) == [["a", "c"], "b", "d"]


@with_grid
def test_client_integrate(plasma):
    plasma.c.layout.integrate_left()
    assert client_tree(plasma) == [["a", "c", "d"], "b"]
    plasma.c.layout.integrate_up()
    assert client_tree(plasma) == [["a", ["c", "d"]], "b"]
    plasma.c.layout.integrate_up()
    plasma.c.layout.integrate_down()
    assert client_tree(plasma) == [["a", ["c", "d"]], "b"]
    plasma.c.layout.integrate_right()
    assert client_tree(plasma) == [["a", "c"], ["b", "d"]]


def test_sizes(plasma):
    Node.priority = Priority.BALANCED
    plasma.test_window("a")
    plasma.test_window("b")
    plasma.c.layout.mode_vertical()
    plasma.test_window("c")
    info = plasma.c.window.info()
    assert info["x"] == 400
    assert info["y"] == 300
    assert info["width"] == 400 - 2
    assert info["height"] == 300 - 2
    plasma.c.layout.grow_height(50)
    info = plasma.c.window.info()
    assert info["height"] == 300 - 2 + 50
    plasma.c.layout.grow_width(50)
    info = plasma.c.window.info()
    assert info["width"] == 400 - 2 + 50
    plasma.c.layout.reset_size()
    info = plasma.c.window.info()
    assert info["height"] == 300 - 2
    plasma.c.layout.set_height(300)
    info = plasma.c.window.info()
    assert info["height"] == 300 - 2
    plasma.c.layout.set_width(250)
    info = plasma.c.window.info()
    assert info["width"] == 250 - 2
    plasma.c.layout.set_size(200)
    info = plasma.c.window.info()
    assert info["height"] == 200 - 2
    plasma.c.layout.grow(10)
    info = plasma.c.window.info()
    assert info["height"] == 210 - 2


def test_remove(plasma):
    a = plasma.test_window("a")
    b = plasma.test_window("b")
    assert client_tree(plasma) == ["a", "b"]
    plasma.kill_window(a)
    assert client_tree(plasma) == ["b"]
    plasma.kill_window(b)
    assert client_tree(plasma) == []


def test_split_mode(plasma):
    plasma.test_window("a")
    plasma.test_window("b")
    plasma.c.layout.mode_horizontal_split()
    plasma.test_window("c")
    assert plasma.c.window.info()["width"] == 200 - 2
    plasma.c.layout.mode_vertical()
    plasma.test_window("d")
    assert plasma.c.window.info()["height"] == 300 - 2
    plasma.test_window("e")
    assert plasma.c.window.info()["height"] == 200 - 2
    plasma.c.layout.mode_vertical_split()
    plasma.test_window("f")
    assert plasma.c.window.info()["height"] == 100 - 2


def test_recent(plasma):
    plasma.test_window("a")
    plasma.test_window("b")
    plasma.test_window("c")
    assert_focused(plasma, "c")
    plasma.c.layout.recent()
    assert_focused(plasma, "b")
    plasma.c.layout.recent()
    assert_focused(plasma, "c")
    plasma.c.layout.next()
    assert_focused(plasma, "a")
    plasma.c.layout.recent()
    assert_focused(plasma, "c")


def test_bug_10():
    """Adding nodes when the correct root dimensions are still unknown
    should not raise an error.
    """
    layout = Plasma()
    layout.add_client(object())
    layout.add_client(object())
