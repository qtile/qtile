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

import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.helpers import HEIGHT, WIDTH
from test.layouts.layout_utils import assert_focus_path, assert_focused


class ColumnsConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        layout.Columns(num_columns=3),
        layout.Columns(margin_on_single=10),
        layout.Columns(margin_on_single=[10, 20, 30, 40]),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


columns_config = pytest.mark.parametrize("manager", [ColumnsConfig], indirect=True)

# This currently only tests the window focus cycle


@columns_config
def test_columns_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("four")

    # test preconditions, columns adds clients at pos after current, in two stacks
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["one"]
    assert columns[1]["clients"] == ["two"]
    assert columns[2]["clients"] == ["four", "three"]
    # last added window has focus
    assert_focused(manager, "four")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "three", "float1", "float2", "one", "two", "four")


@columns_config
def test_columns_swap_column_left(manager):
    manager.test_window("1")
    manager.test_window("2")
    manager.test_window("3")
    manager.test_window("4")

    # test preconditions
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["1"]
    assert columns[1]["clients"] == ["2"]
    assert columns[2]["clients"] == ["4", "3"]
    assert_focused(manager, "4")

    # assert columns are swapped left
    manager.c.layout.swap_column_left()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["1"]
    assert columns[1]["clients"] == ["4", "3"]
    assert columns[2]["clients"] == ["2"]

    manager.c.layout.swap_column_left()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["4", "3"]
    assert columns[1]["clients"] == ["1"]
    assert columns[2]["clients"] == ["2"]

    manager.c.layout.swap_column_left()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["2"]
    assert columns[1]["clients"] == ["1"]
    assert columns[2]["clients"] == ["4", "3"]


@columns_config
def test_columns_swap_column_right(manager):
    manager.test_window("1")
    manager.test_window("2")
    manager.test_window("3")
    manager.test_window("4")

    # test preconditions
    assert manager.c.layout.info()["columns"][0]["clients"] == ["1"]
    assert manager.c.layout.info()["columns"][1]["clients"] == ["2"]
    assert manager.c.layout.info()["columns"][2]["clients"] == ["4", "3"]
    assert_focused(manager, "4")

    # assert columns are swapped right
    manager.c.layout.swap_column_right()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["4", "3"]
    assert columns[1]["clients"] == ["2"]
    assert columns[2]["clients"] == ["1"]

    manager.c.layout.swap_column_right()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["2"]
    assert columns[1]["clients"] == ["4", "3"]
    assert columns[2]["clients"] == ["1"]

    manager.c.layout.swap_column_right()
    columns = manager.c.layout.info()["columns"]
    assert columns[0]["clients"] == ["2"]
    assert columns[1]["clients"] == ["1"]
    assert columns[2]["clients"] == ["4", "3"]


@columns_config
def test_columns_margins_single(manager):
    manager.test_window("1")

    # no margin
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == WIDTH
    assert info["height"] == HEIGHT

    # single margin for all sides
    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["x"] == 10
    assert info["y"] == 10
    assert info["width"] == WIDTH - 20
    assert info["height"] == HEIGHT - 20

    # one margin for each side (N E S W)
    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["x"] == 40
    assert info["y"] == 10
    assert info["width"] == WIDTH - 60
    assert info["height"] == HEIGHT - 40


def get_column_width(col_index, manager):
    return int(manager.c.layout.eval(f"self.columns[{col_index}].width")[1])


@columns_config
def test_columns_serdes(manager):
    # setup windows
    manager.test_window("1")
    manager.test_window("2")
    manager.test_window("3")
    manager.test_window("4")

    manager.c.layout.shuffle_left()
    manager.c.layout.shuffle_left()
    manager.c.layout.grow_right()
    manager.c.layout.grow_down()
    manager.c.layout.toggle_split()

    # serialize layout
    data = manager.c.layout.eval("self.serialize()")[1]

    # change layout
    manager.c.layout.toggle_split()
    manager.c.layout.grow_up()
    manager.c.layout.grow_left()
    manager.c.layout.shuffle_right()
    manager.c.layout.shuffle_right()
    manager.c.layout.left()

    # deserialize layout
    manager.c.layout.eval(f"self.deserialize({data})")

    # check
    columns = manager.c.layout.info()["columns"]

    assert columns[0]["clients"] == ["4", "1"]
    assert columns[0]["heights"] == [110, 90]
    assert columns[1]["clients"] == ["2"]
    assert columns[2]["clients"] == ["3"]

    assert get_column_width(0, manager) == 110
    assert get_column_width(1, manager) == 90

    assert not columns[0]["split"]

    assert_focused(manager, "4")
