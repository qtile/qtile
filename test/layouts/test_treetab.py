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
from test.conftest import no_xinerama
from test.layouts.layout_utils import assert_focus_path, assert_focused


class TreeTabConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.TreeTab(sections=["Foo", "Bar"]),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def treetab_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [TreeTabConfig], indirect=True)(x))


@treetab_config
def test_window(qtile):
    pytest.importorskip("tkinter")
    # setup 3 tiled and two floating clients
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_dialog("float1")
    qtile.test_dialog("float2")
    qtile.test_window("three")

    # test preconditions, columns adds clients at pos of current, in two stacks
    assert qtile.c.layout.info()['clients'] == ['one', 'three', 'two']
    assert qtile.c.layout.info()['sections'] == ['Foo', 'Bar']
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Bar': []}

    # last added window has focus
    assert_focused(qtile, "three")
    qtile.c.layout.up()
    assert_focused(qtile, "two")
    qtile.c.layout.down()
    assert_focused(qtile, "three")

    # test command move_up/down
    qtile.c.layout.move_up()
    assert qtile.c.layout.info()['clients'] == ['one', 'three', 'two']
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three'], ['two']], 'Bar': []}
    qtile.c.layout.move_down()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Bar': []}

    # section_down/up
    qtile.c.layout.up()  # focus two
    qtile.c.layout.section_down()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three']], 'Bar': [['two']]}
    qtile.c.layout.section_up()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three'], ['two']], 'Bar': []}

    # del_section
    qtile.c.layout.up()  # focus three
    qtile.c.layout.section_down()
    qtile.c.layout.del_section("Bar")
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']]}

    # add_section
    qtile.c.layout.add_section('Baz')
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Baz': []}
    qtile.c.layout.del_section('Baz')

    # move_left/right
    qtile.c.layout.move_left()  # no effect for top-level children
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']]}
    qtile.c.layout.move_right()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three']]]}
    qtile.c.layout.move_right()  # no effect
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three']]]}
    qtile.test_window("four")
    qtile.c.layout.move_right()
    qtile.c.layout.up()
    qtile.test_window("five")
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three', ['four']], ['five']]]}

    # expand/collapse_branch, and check focus order
    qtile.c.layout.up()
    qtile.c.layout.up()  # focus three
    qtile.c.layout.collapse_branch()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three'], ['five']]]}
    assert_focus_path(qtile, 'five', 'float1', 'float2', 'one', 'two', 'three')
    qtile.c.layout.expand_branch()
    assert qtile.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three', ['four']], ['five']]]}
    assert_focus_path(qtile, 'four', 'five', 'float1', 'float2', 'one', 'two', 'three')


@treetab_config
def test_sort_windows(qtile):
    def sorter(window):
        try:
            if int(window.name) % 2 == 0:
                return 'Even'
            else:
                return 'Odd'
        except ValueError:
            return 'Bar'

    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("101")
    qtile.test_window("102")
    qtile.test_window("103")
    assert qtile.c.layout.info()['client_trees'] == {
        'Foo': [['one'], ['two'], ['101'], ['102'], ['103']],
        'Bar': []
    }
    return  # TODO how to serialize a function object? i.e. `sorter`
    qtile.c.layout.sort_windows(sorter)
    assert qtile.c.layout.info()['client_trees'] == {
        'Foo': [],
        'Bar': [['one'], ['two']],
        'Even': [['102']],
        'Odd': [['101'], ['103']]
    }
