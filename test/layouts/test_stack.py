# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Chris Wesseling
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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..conftest import no_xinerama
from .layout_utils import assertFocused, assertFocusPath

class StackConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Stack(num_stacks=2),
        layout.Stack(num_stacks=1),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False
    focus_on_mapped_windows = True


stack_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [StackConfig], indirect=True)(x))


def _stacks(self):
    stacks = []
    for i in self.c.layout.info()["stacks"]:
        windows = i["clients"]
        current = i["current"]
        stacks.append(windows[current:] + windows[:current])
    return stacks


@stack_config
def test_stack_commands(qtile):
    assert qtile.c.layout.info()["current_stack"] == 0
    qtile.testWindow("one")
    assert _stacks(qtile) == [["one"], []]
    assert qtile.c.layout.info()["current_stack"] == 0
    qtile.testWindow("two")
    assert _stacks(qtile) == [["one"], ["two"]]
    assert qtile.c.layout.info()["current_stack"] == 1
    qtile.testWindow("three")
    assert _stacks(qtile) == [["one"], ["three", "two"]]
    assert qtile.c.layout.info()["current_stack"] == 1

    qtile.c.layout.delete()
    assert _stacks(qtile) == [["one", "three", "two"]]
    info = qtile.c.groups()["a"]
    assert info["focus"] == "one"
    qtile.c.layout.delete()
    assert len(_stacks(qtile)) == 1

    qtile.c.layout.add()
    assert _stacks(qtile) == [["one", "three", "two"], []]

    qtile.c.layout.rotate()
    assert _stacks(qtile) == [[], ["one", "three", "two"]]


@stack_config
def test_stack_cmd_down(qtile):
    qtile.c.layout.down()


@stack_config
def test_stack_addremove(qtile):
    one = qtile.testWindow("one")
    qtile.c.layout.next()
    two = qtile.testWindow("two")
    three = qtile.testWindow("three")
    assert _stacks(qtile) == [['one'], ['three', 'two']]
    assert qtile.c.layout.info()["current_stack"] == 1
    qtile.kill_window(three)
    assert qtile.c.layout.info()["current_stack"] == 1
    qtile.kill_window(two)
    assert qtile.c.layout.info()["current_stack"] == 0
    qtile.c.layout.next()
    two = qtile.testWindow("two")
    qtile.c.layout.next()
    assert qtile.c.layout.info()["current_stack"] == 0
    qtile.kill_window(one)
    assert qtile.c.layout.info()["current_stack"] == 1


@stack_config
def test_stack_rotation(qtile):
    qtile.c.layout.delete()
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    assert _stacks(qtile) == [["three", "two", "one"]]
    qtile.c.layout.down()
    assert _stacks(qtile) == [["one", "three", "two"]]
    qtile.c.layout.up()
    assert _stacks(qtile) == [["three", "two", "one"]]
    qtile.c.layout.down()
    qtile.c.layout.down()
    assert _stacks(qtile) == [["two", "one", "three"]]


@stack_config
def test_stack_nextprev(qtile):
    qtile.c.layout.add()
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    three = qtile.testWindow("three")

    assert qtile.c.groups()["a"]["focus"] == "three"
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "one"

    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] == "three"
    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] == "two"

    qtile.c.layout.next()
    qtile.c.layout.next()
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "two"

    qtile.kill_window(three)
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "one"
    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] == "two"
    qtile.c.layout.next()
    qtile.kill_window(two)
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "one"

    qtile.kill_window(one)
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] is None
    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] is None


@stack_config
def test_stack_window_removal(qtile):
    qtile.c.layout.next()
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    qtile.c.layout.down()
    qtile.kill_window(two)


@stack_config
def test_stack_split(qtile):
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    three = qtile.testWindow("three")
    stacks = qtile.c.layout.info()["stacks"]
    assert not stacks[1]["split"]
    qtile.c.layout.toggle_split()
    stacks = qtile.c.layout.info()["stacks"]
    assert stacks[1]["split"]


@stack_config
def test_stack_shuffle(qtile):
    qtile.c.next_layout()
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    three = qtile.testWindow("three")

    stack = qtile.c.layout.info()["stacks"][0]
    assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        qtile.c.layout.shuffle_up()
        stack = qtile.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        qtile.c.layout.shuffle_down()
        stack = qtile.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"


@stack_config
def test_stack_client_to(qtile):
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    assert qtile.c.layout.info()["stacks"][0]["clients"] == ["one"]
    qtile.c.layout.client_to_previous()
    assert qtile.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]
    qtile.c.layout.client_to_previous()
    assert qtile.c.layout.info()["stacks"][0]["clients"] == ["one"]
    assert qtile.c.layout.info()["stacks"][1]["clients"] == ["two"]
    qtile.c.layout.client_to_next()
    assert qtile.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]


@stack_config
def test_stack_info(qtile):
    one = qtile.testWindow("one")
    assert qtile.c.layout.info()["stacks"]

@stack_config
def test_stack_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("float1")
    qtile.c.window.toggle_floating()
    qtile.testWindow("float2")
    qtile.c.window.toggle_floating()
    qtile.testWindow("three")

    # test preconditions, stack adds clients at pos of current
    assert qtile.c.layout.info()['clients'] == ['three', 'one', 'two']
    # last added window has focus
    assertFocused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assertFocusPath(qtile, 'one', 'two', 'float1', 'float2', 'three')
