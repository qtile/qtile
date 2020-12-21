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
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def treetab_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [TreeTabConfig], indirect=True)(x))


@treetab_config
def test_window(self):
    pytest.importorskip("tkinter")
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_dialog("float1")
    self.test_dialog("float2")
    self.test_window("three")

    # test preconditions, columns adds clients at pos of current, in two stacks
    assert self.c.layout.info()['clients'] == ['one', 'three', 'two']
    assert self.c.layout.info()['sections'] == ['Foo', 'Bar']
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Bar': []}

    # last added window has focus
    assert_focused(self, "three")
    self.c.layout.up()
    assert_focused(self, "two")
    self.c.layout.down()
    assert_focused(self, "three")

    # test command move_up/down
    self.c.layout.move_up()
    assert self.c.layout.info()['clients'] == ['one', 'three', 'two']
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three'], ['two']], 'Bar': []}
    self.c.layout.move_down()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Bar': []}

    # section_down/up
    self.c.layout.up()  # focus two
    self.c.layout.section_down()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three']], 'Bar': [['two']]}
    self.c.layout.section_up()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['three'], ['two']], 'Bar': []}

    # del_section
    self.c.layout.up()  # focus three
    self.c.layout.section_down()
    self.c.layout.del_section("Bar")
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']]}

    # add_section
    self.c.layout.add_section('Baz')
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']], 'Baz': []}
    self.c.layout.del_section('Baz')

    # move_left/right
    self.c.layout.move_left()  # no effect for top-level children
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two'], ['three']]}
    self.c.layout.move_right()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three']]]}
    self.c.layout.move_right()  # no effect
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three']]]}
    self.test_window("four")
    self.c.layout.move_right()
    self.c.layout.up()
    self.test_window("five")
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three', ['four']], ['five']]]}

    # expand/collapse_branch, and check focus order
    self.c.layout.up()
    self.c.layout.up()  # focus three
    self.c.layout.collapse_branch()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three'], ['five']]]}
    assert_focus_path(self, 'five', 'float1', 'float2', 'one', 'two', 'three')
    self.c.layout.expand_branch()
    assert self.c.layout.info()['client_trees'] == {'Foo': [['one'], ['two', ['three', ['four']], ['five']]]}
    assert_focus_path(self, 'four', 'five', 'float1', 'float2', 'one', 'two', 'three')


@treetab_config
def test_sort_windows(self):
    def sorter(window):
        try:
            if int(window.name) % 2 == 0:
                return 'Even'
            else:
                return 'Odd'
        except ValueError:
            return 'Bar'

    self.test_window("one")
    self.test_window("two")
    self.test_window("101")
    self.test_window("102")
    self.test_window("103")
    assert self.c.layout.info()['client_trees'] == {
        'Foo': [['one'], ['two'], ['101'], ['102'], ['103']],
        'Bar': []
    }
    return  # TODO how to serialize a function object? i.e. `sorter`
    self.c.layout.sort_windows(sorter)
    assert self.c.layout.info()['client_trees'] == {
        'Foo': [],
        'Bar': [['one'], ['two']],
        'Even': [['102']],
        'Odd': [['101'], ['103']]
    }
