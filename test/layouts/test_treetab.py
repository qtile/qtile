# Copyright (c) 2019 Guangwang Huang
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
from test.layouts.layout_utils import assert_focus_path, assert_focused


class TreeTabConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        layout.TreeTab(sections=["Foo", "Bar"]),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


treetab_config = pytest.mark.parametrize("manager", [TreeTabConfig], indirect=True)


@treetab_config
def test_window(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1", floating=True)
    manager.test_window("float2", floating=True)
    manager.test_window("three")

    # test preconditions, columns adds clients at pos of current, in two stacks
    assert manager.c.layout.info()["clients"] == ["one", "three", "two"]
    assert manager.c.layout.info()["sections"] == ["Foo", "Bar"]
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two"], ["three"]],
        "Bar": [],
    }

    # last added window has focus
    assert_focused(manager, "three")
    manager.c.layout.up()
    assert_focused(manager, "two")
    manager.c.layout.down()
    assert_focused(manager, "three")

    # test command move_up/down
    manager.c.layout.move_up()
    assert manager.c.layout.info()["clients"] == ["one", "three", "two"]
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["three"], ["two"]],
        "Bar": [],
    }
    manager.c.layout.move_down()
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two"], ["three"]],
        "Bar": [],
    }

    # section_down/up
    manager.c.layout.up()  # focus two
    manager.c.layout.section_down()
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["three"]],
        "Bar": [["two"]],
    }
    manager.c.layout.section_up()
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["three"], ["two"]],
        "Bar": [],
    }

    # del_section
    manager.c.layout.up()  # focus three
    manager.c.layout.section_down()
    manager.c.layout.del_section("Bar")
    assert manager.c.layout.info()["client_trees"] == {"Foo": [["one"], ["two"], ["three"]]}

    # add_section
    manager.c.layout.add_section("Baz")
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two"], ["three"]],
        "Baz": [],
    }
    manager.c.layout.del_section("Baz")

    # move_left/right
    manager.c.layout.move_left()  # no effect for top-level children
    assert manager.c.layout.info()["client_trees"] == {"Foo": [["one"], ["two"], ["three"]]}
    manager.c.layout.move_right()
    assert manager.c.layout.info()["client_trees"] == {"Foo": [["one"], ["two", ["three"]]]}
    manager.c.layout.move_right()  # no effect
    assert manager.c.layout.info()["client_trees"] == {"Foo": [["one"], ["two", ["three"]]]}
    manager.test_window("four")
    manager.c.layout.move_right()
    manager.c.layout.up()
    manager.test_window("five")
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two", ["three", ["four"]], ["five"]]]
    }

    # expand/collapse_branch, and check focus order
    manager.c.layout.up()
    manager.c.layout.up()  # focus three
    manager.c.layout.collapse_branch()
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two", ["three"], ["five"]]]
    }
    assert_focus_path(manager, "five", "float1", "float2", "one", "two", "three")
    manager.c.layout.expand_branch()
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two", ["three", ["four"]], ["five"]]]
    }
    assert_focus_path(manager, "four", "five", "float1", "float2", "one", "two", "three")


@treetab_config
def test_sort_windows(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("101")
    manager.test_window("102")
    manager.test_window("103")
    assert manager.c.layout.info()["client_trees"] == {
        "Foo": [["one"], ["two"], ["101"], ["102"], ["103"]],
        "Bar": [],
    }
    """
    # TODO how to serialize a function object? i.e. `sorter`:

    def sorter(window):
        try:
            if int(window.name) % 2 == 0:
                return 'Even'
            else:
                return 'Odd'
        except ValueError:
            return 'Bar'

    manager.c.layout.sort_windows(sorter)
    assert manager.c.layout.info()['client_trees'] == {
        'Foo': [],
        'Bar': [['one'], ['two']],
        'Even': [['102']],
        'Odd': [['101'], ['103']]
    }
    """
