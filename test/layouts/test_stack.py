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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..utils import Xephyr


class StackConfig:
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


def _stacks(self):
    stacks = []
    for i in self.c.layout.info()["stacks"]:
        windows = i["clients"]
        current = i["current"]
        stacks.append(windows[current:] + windows[:current])
    return stacks


@Xephyr(False, StackConfig())
def test_stack_commands(self):
    assert self.c.layout.info()["current_stack"] == 0
    self.testWindow("one")
    assert _stacks(self) == [["one"], []]
    assert self.c.layout.info()["current_stack"] == 0
    self.testWindow("two")
    assert _stacks(self) == [["one"], ["two"]]
    assert self.c.layout.info()["current_stack"] == 1
    self.testWindow("three")
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


@Xephyr(False, StackConfig())
def test_stack_cmd_down(self):
    self.c.layout.down()


@Xephyr(False, StackConfig())
def test_stack_addremove(self):
    one = self.testWindow("one")
    self.c.layout.next()
    two = self.testWindow("two")
    three = self.testWindow("three")
    assert _stacks(self) == [['one'], ['three', 'two']]
    assert self.c.layout.info()["current_stack"] == 1
    self.kill(three)
    assert self.c.layout.info()["current_stack"] == 1
    self.kill(two)
    assert self.c.layout.info()["current_stack"] == 0
    self.c.layout.next()
    two = self.testWindow("two")
    self.c.layout.next()
    assert self.c.layout.info()["current_stack"] == 0
    self.kill(one)
    assert self.c.layout.info()["current_stack"] == 1


@Xephyr(False, StackConfig())
def test_stack_rotation(self):
    self.c.layout.delete()
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    assert _stacks(self) == [["one", "three", "two"]]
    self.c.layout.up()
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    self.c.layout.down()
    assert _stacks(self) == [["two", "one", "three"]]


@Xephyr(False, StackConfig())
def test_stack_nextprev(self):
    self.c.layout.add()
    one = self.testWindow("one")
    two = self.testWindow("two")
    three = self.testWindow("three")

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

    self.kill(three)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.layout.next()
    self.kill(two)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"

    self.kill(one)
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == None
    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == None


@Xephyr(False, StackConfig())
def test_stack_window_removal(self):
    self.c.layout.next()
    one = self.testWindow("one")
    two = self.testWindow("two")
    self.c.layout.down()
    self.kill(two)


@Xephyr(False, StackConfig())
def test_stack_split(self):
    one = self.testWindow("one")
    two = self.testWindow("two")
    three = self.testWindow("three")
    stacks = self.c.layout.info()["stacks"]
    assert not stacks[1]["split"]
    self.c.layout.toggle_split()
    stacks = self.c.layout.info()["stacks"]
    assert stacks[1]["split"]


@Xephyr(False, StackConfig())
def test_stack_shuffle(self):
    self.c.next_layout()
    one = self.testWindow("one")
    two = self.testWindow("two")
    three = self.testWindow("three")

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


@Xephyr(False, StackConfig())
def test_stack_client_to(self):
    one = self.testWindow("one")
    two = self.testWindow("two")
    assert self.c.layout.info()["stacks"][0]["clients"] == ["one"]
    self.c.layout.client_to_previous()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]
    self.c.layout.client_to_previous()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["one"]
    assert self.c.layout.info()["stacks"][1]["clients"] == ["two"]
    self.c.layout.client_to_next()
    assert self.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]


@Xephyr(False, StackConfig())
def test_stack_info(self):
    one = self.testWindow("one")
    assert self.c.layout.info()["stacks"]
