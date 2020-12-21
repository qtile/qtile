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


class TileConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Tile(),
        layout.Tile(master_length=2)
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def tile_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [TileConfig], indirect=True)(x))


@tile_config
def test_tile_updown(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]
    self.c.layout.shuffle_down()
    assert self.c.layout.info()["clients"] == ["two", "one", "three"]
    self.c.layout.shuffle_up()
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]


@tile_config
def test_tile_nextprev(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")

    assert self.c.layout.info()["clients"] == ["three", "two", "one"]
    assert self.c.groups()["a"]["focus"] == "three"

    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "two"

    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "three"

    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "one"

    self.c.layout.next()
    self.c.layout.next()
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"


@tile_config
def test_tile_master_and_slave(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")

    assert self.c.layout.info()["master"] == ["three"]
    assert self.c.layout.info()["slave"] == ["two", "one"]

    self.c.next_layout()
    assert self.c.layout.info()["master"] == ["three", "two"]
    assert self.c.layout.info()["slave"] == ["one"]


@tile_config
def test_tile_remove(self):
    one = self.test_window("one")
    self.test_window("two")
    three = self.test_window("three")

    assert self.c.layout.info()["master"] == ["three"]
    self.kill_window(one)
    assert self.c.layout.info()["master"] == ["three"]
    self.kill_window(three)
    assert self.c.layout.info()["master"] == ["two"]


@tile_config
def test_tile_window_focus_cycle(self):
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_window("float1")
    self.c.window.toggle_floating()
    self.test_window("float2")
    self.c.window.toggle_floating()
    self.test_window("three")

    # test preconditions, Tile adds (by default) clients at pos of current
    assert self.c.layout.info()['clients'] == ['three', 'two', 'one']
    # last added window has focus
    assert_focused(self, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(self, 'two', 'one', 'float1', 'float2', 'three')
