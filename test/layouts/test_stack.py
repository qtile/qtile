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

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.conftest import no_xinerama
from test.layouts.layout_utils import assert_focus_path, assert_focused


class StackConfig(Config):
    auto_fullscreen = True
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
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def stack_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [StackConfig], indirect=True)(x))


def _stacks(self):
    stacks = []
    for i in self.c.layout.info()["stacks"]:
        windows = i["clients"]
        current = i["current"]
        stacks.append(windows[current:] + windows[:current])
    return stacks


@stack_config
def test_stack_commands(self):
    assert self.c.layout.info()["current_stack"] == 0
    self.test_window("one")
    assert _stacks(self) == [["one"], []]
    assert self.c.layout.info()["current_stack"] == 0
    self.test_window("two")
    assert _stacks(self) == [["one"], ["two"]]
    assert self.c.layout.info()["current_stack"] == 1
    self.test_window("three")
    assert _stacks(self) == [["one"], ["three", "two"]]
    assert self.c.layout.info()["current_stack"] == 1

    self.c.layout.delete()
    assert _stacks(self) == [["one", "three", "two"]]
    info = self.c.groups()["a"]
    assert info["focus"] == "one"
    self.c.layout.delete()
    assert len(_stacks(self)) == 1

    self.c.layout.add()
    assert _stacks(self) == [["one", "three", "two"], []]

    self.c.layout.rotate()
    assert _stacks(self) == [[], ["one", "three", "two"]]


@stack_config
def test_stack_cmd_down(self):
    self.c.layout.down()


@stack_config
def test_stack_addremove(self):
    one = self.test_window("one")
    self.c.layout.next()
    two = self.test_window("two")
    three = self.test_window("three")
    assert _stacks(self) == [['one'], ['three', 'two']]
    assert self.c.layout.info()["current_stack"] == 1
    self.kill_window(three)
    assert self.c.layout.info()["current_stack"] == 1
    self.kill_window(two)
    assert self.c.layout.info()["current_stack"] == 0
    self.c.layout.next()
    two = self.test_window("two")
    self.c.layout.next()
    assert self.c.layout.info()["current_stack"] == 0
    self.kill_window(one)
    assert self.c.layout.info()["current_stack"] == 1


@stack_config
def test_stack_rotation(self):
    self.c.layout.delete()
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    assert _stacks(self) == [["two", "one", "three"]]
    self.c.layout.up()
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    self.c.layout.down()
    assert _stacks(self) == [["one", "three", "two"]]


@stack_config
def test_stack_nextprev(self):
    self.c.layout.add()
    one = self.test_window("one")
    two = self.test_window("two")
    three = self.test_window("three")

    assert self.c.groups()["a"]["focus"] == "three"
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"

    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "three"
    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "two"

    self.c.layout.next()
    self.c.layout.next()
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "two"

    self.kill_window(three)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.layout.next()
    self.kill_window(two)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"

    self.kill_window(one)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] is None
    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] is None


@stack_config
def test_stack_window_removal(self):
    self.c.layout.next()
    self.test_window("one")
    two = self.test_window("two")
    self.c.layout.down()
    self.kill_window(two)


@stack_config
def test_stack_split(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    stacks = self.c.layout.info()["stacks"]
    assert not stacks[1]["split"]
    self.c.layout.toggle_split()
    stacks = self.c.layout.info()["stacks"]
    assert stacks[1]["split"]


@stack_config
def test_stack_shuffle(self):
    self.c.next_layout()
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")

    stack = self.c.layout.info()["stacks"][0]
    assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        self.c.layout.shuffle_up()
        stack = self.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        self.c.layout.shuffle_down()
        stack = self.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"


@stack_config
def test_stack_client_to(self):
    self.test_window("one")
    self.test_window("two")
    assert self.c.layout.info()["stacks"][0]["clients"] == ["one"]
    self.c.layout.client_to_previous()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]
    self.c.layout.client_to_previous()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["one"]
    assert self.c.layout.info()["stacks"][1]["clients"] == ["two"]
    self.c.layout.client_to_next()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]


@stack_config
def test_stack_info(self):
    self.test_window("one")
    assert self.c.layout.info()["stacks"]


@stack_config
def test_stack_window_focus_cycle(self):
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_window("float1")
    self.c.window.toggle_floating()
    self.test_window("float2")
    self.c.window.toggle_floating()
    self.test_window("three")

    # test preconditions, stack adds clients at pos of current
    assert self.c.layout.info()['clients'] == ['three', 'one', 'two']
    # last added window has focus
    assert_focused(self, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(self, 'one', 'two', 'float1', 'float2', 'three')
