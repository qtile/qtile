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
from libqtile.resources.default_config import floating_layout
from test.helpers import HEIGHT, WIDTH
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused

MARGIN = 10
MARGIN_ON_SINGLE = 30
BORDER = 2


class ColumnsConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [
        layout.Columns(num_columns=3, border=BORDER),
        layout.Columns(margin=MARGIN, border=BORDER),
        layout.Columns(margin=MARGIN, margin_on_single=MARGIN_ON_SINGLE, border=BORDER),
    ]
    floating_layout = floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


class ColumnsSingleBorderDisabledConfig(ColumnsConfig):
    layouts = [layout.Columns(border_on_single=False, single_border_width=2, border_width=4)]


class ColumnsSingleBorderEnabledConfig(ColumnsConfig):
    layouts = [layout.Columns(border_on_single=True, single_border_width=2, border_width=4)]


class ColumnsLeftAlign(ColumnsConfig):
    layouts = [layout.Columns(align=layout.Columns._left, border_width=0)]


class ColumnsInitialRatio(ColumnsConfig):
    layouts = [
        layout.Columns(initial_ratio=3, border_width=0),
        layout.Columns(initial_ratio=3, align=layout.Columns._left, border_width=0),
    ]


columns_config = pytest.mark.parametrize("manager", [ColumnsConfig], indirect=True)
columns_single_border_disabled_config = pytest.mark.parametrize(
    "manager", [ColumnsSingleBorderDisabledConfig], indirect=True
)
columns_single_border_enabled_config = pytest.mark.parametrize(
    "manager", [ColumnsSingleBorderEnabledConfig], indirect=True
)
columns_left_align = pytest.mark.parametrize("manager", [ColumnsLeftAlign], indirect=True)
columns_initial_ratio = pytest.mark.parametrize("manager", [ColumnsInitialRatio], indirect=True)


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


def window_padding(margin, border):
    return 2 * border + margin


def window_size(available_space, num_clients, margin, border):
    # rounding can lead to rounding erros
    per_window_padding = window_padding(margin, border)
    total_padding = num_clients * per_window_padding + margin  # one margin offset
    return (available_space - total_padding) / num_clients


def windows_in_current_column(self):
    for column in self.c.layout.info()["columns"]:
        for client in column["clients"]:
            if self.c.window.info()["name"] == str(client):
                return len(column["clients"])
    assert False


@columns_config
def test_columns_margins_single_window(manager):
    manager.test_window("1")

    # no margin
    assert_dimensions(manager, 0, 0, WIDTH, HEIGHT)

    # margin
    manager.c.next_layout()
    assert_dimensions(
        manager,
        MARGIN,
        MARGIN,
        WIDTH - 2 * MARGIN,
        HEIGHT - 2 * MARGIN,
    )

    # margin_on_single is set
    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["x"] == 30
    assert info["y"] == 30
    assert info["width"] == WIDTH - 60
    assert info["height"] == HEIGHT - 60

    assert_dimensions(
        manager,
        MARGIN_ON_SINGLE,
        MARGIN_ON_SINGLE,
        WIDTH - 2 * MARGIN_ON_SINGLE,
        HEIGHT - 2 * MARGIN_ON_SINGLE,
    )

    # one column but mulitple windows
    manager.test_window("2")
    manager.c.layout.shuffle_left()
    manager.c.layout.toggle_split()
    assert_dimensions(
        manager,
        MARGIN_ON_SINGLE,
        MARGIN_ON_SINGLE,
        WIDTH - 2 * MARGIN_ON_SINGLE,
        HEIGHT - 2 * MARGIN_ON_SINGLE,
    )


@columns_single_border_disabled_config
def test_columns_single_border_disabled(manager):
    manager.test_window("1")
    assert_dimensions(manager, 0, 0, WIDTH, HEIGHT)
    manager.test_window("2")
    assert_dimensions(manager, WIDTH / 2, 0, WIDTH / 2 - 8, HEIGHT - 8)


@columns_single_border_enabled_config
def test_columns_single_border_enabled(manager):
    manager.test_window("1")
    assert_dimensions(manager, 0, 0, WIDTH - 4, HEIGHT - 4)
    manager.test_window("2")
    assert_dimensions(manager, WIDTH / 2, 0, WIDTH / 2 - 8, HEIGHT - 8)


@columns_left_align
def test_columns_left_align(manager):
    # window 1: fullscreen
    manager.test_window("1")
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == WIDTH
    assert info["height"] == HEIGHT

    # window 2: left
    manager.test_window("2")
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == WIDTH / 2
    assert info["height"] == HEIGHT

    # window 3: top left
    manager.test_window("3")
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == WIDTH / 2
    assert info["height"] == HEIGHT / 2


@columns_initial_ratio
def test_columns_initial_ratio_right(manager):
    manager.test_window("1")
    manager.test_window("2")

    # initial_ratio is 3 (i.e. main column is 3 times size of secondary column)
    # so secondary column is 1/4 of screen width
    info = manager.c.window.info()
    assert info["x"] == 3 * WIDTH / 4
    assert info["y"] == 0
    assert info["width"] == WIDTH / 4
    assert info["height"] == HEIGHT

    # Growing right means secondary column is now smaller
    manager.c.layout.grow_right()
    info = manager.c.window.info()
    assert info["width"] < WIDTH / 4

    # Reset to restore initial_ratio
    manager.c.layout.reset()
    info = manager.c.window.info()
    assert info["width"] == WIDTH / 4

    # Normalize to make columns equal
    manager.c.layout.normalize()
    info = manager.c.window.info()
    assert info["width"] == WIDTH / 2


@columns_initial_ratio
def test_columns_initial_ratio_left(manager):
    manager.c.next_layout()
    manager.test_window("1")
    manager.test_window("2")

    # initial_ratio is 3 (i.e. main column is 3 times size of secondary column)
    # so secondary column is 1/4 of screen width
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == WIDTH / 4
    assert info["height"] == HEIGHT

    # Growing right means secondary column is now smaller
    manager.c.layout.grow_left()
    info = manager.c.window.info()
    assert info["width"] < WIDTH / 4

    # Reset to restore initial_ratio
    manager.c.layout.reset()
    info = manager.c.window.info()
    assert info["width"] == WIDTH / 4

    # Normalize to make columns equal
    manager.c.layout.normalize()
    info = manager.c.window.info()
    assert info["width"] == WIDTH / 2

@columns_config
def test_columns_margins_muliple_windows_three_columns(manager):
    num_columns = 3
    for i in range(num_columns):
        manager.test_window(str(i))

    # start with the leftmost window
    manager.c.layout.left()
    manager.c.layout.left()

    win_width_unrounded = window_size(WIDTH, num_columns, 0, BORDER)
    win_width = round(win_width_unrounded)
    win_height = round(window_size(HEIGHT, windows_in_current_column(manager), 0, BORDER))
    padding = window_padding(0, BORDER)

    assert_dimensions(manager, 0, 0, win_width, win_height)

    manager.c.layout.right()
    assert_dimensions(manager, win_width + padding, 0, win_width, win_height)

    manager.c.layout.right()
    # rounding before multiplying by 2 leads to rounding error
    assert_dimensions(
        manager, round(2 * (win_width_unrounded + padding)), 0, win_width, win_height
    )


@columns_config
def test_columns_margins_muliple_windows_margin(manager):
    num_windows = 3
    for i in range(num_windows):
        manager.test_window(str(i))

    manager.c.next_layout()  # go to the margin layout
    manager.c.layout.left()  # start with the leftmost window

    columns = manager.c.layout.info()["columns"]
    num_columns = len(columns)
    num_windows = windows_in_current_column(manager)

    win_width = round(window_size(WIDTH, num_columns, MARGIN, BORDER))
    win_height = round(window_size(HEIGHT, num_windows, MARGIN, BORDER))
    assert_dimensions(manager, MARGIN, MARGIN, win_width, win_height)

    manager.c.layout.right()  # move to the other column
    num_windows = windows_in_current_column(manager)

    padding = window_padding(MARGIN, BORDER)
    win_height = round(window_size(HEIGHT, num_windows, MARGIN, BORDER))
    assert_dimensions(
        manager,
        MARGIN + win_width + padding,
        MARGIN,
        win_width,
        win_height,
    )

    manager.c.layout.down()  # move to the other column
    assert_dimensions(
        manager,
        MARGIN + win_width + padding,
        MARGIN + win_height + padding,
        win_width,
        win_height,
    )
