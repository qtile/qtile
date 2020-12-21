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


class MaxConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Max()
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


def max_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MaxConfig], indirect=True)(x))


@max_config
def test_max_simple(self):
    self.test_window("one")
    assert self.c.layout.info()["clients"] == ["one"]
    self.test_window("two")
    assert self.c.layout.info()["clients"] == ["one", "two"]


@max_config
def test_max_updown(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    assert self.c.layout.info()["clients"] == ["one", "two", "three"]
    self.c.layout.up()
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.layout.down()
    assert self.c.groups()["a"]["focus"] == "three"


@max_config
def test_max_remove(self):
    self.test_window("one")
    two = self.test_window("two")
    assert self.c.layout.info()["clients"] == ["one", "two"]
    self.kill_window(two)
    assert self.c.layout.info()["clients"] == ["one"]


@max_config
def test_max_window_focus_cycle(self):
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_window("float1")
    self.c.window.toggle_floating()
    self.test_window("float2")
    self.c.window.toggle_floating()
    self.test_window("three")

    # test preconditions
    assert self.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assert_focused(self, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(self, 'float1', 'float2', 'one', 'two', 'three')
