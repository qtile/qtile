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
    return no_xinerama(pytest.mark.parametrize("manager", [TileConfig], indirect=True)(x))


@tile_config
def test_tile_updown(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    assert manager.c.layout.info()["clients"] == ["three", "two", "one"]
    manager.c.layout.shuffle_down()
    assert manager.c.layout.info()["clients"] == ["two", "one", "three"]
    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["clients"] == ["three", "two", "one"]


@tile_config
def test_tile_nextprev(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    assert manager.c.layout.info()["clients"] == ["three", "two", "one"]
    assert manager.c.groups()["a"]["focus"] == "three"

    manager.c.layout.next()
    assert manager.c.groups()["a"]["focus"] == "two"

    manager.c.layout.previous()
    assert manager.c.groups()["a"]["focus"] == "three"

    manager.c.layout.previous()
    assert manager.c.groups()["a"]["focus"] == "one"

    manager.c.layout.next()
    manager.c.layout.next()
    manager.c.layout.next()
    assert manager.c.groups()["a"]["focus"] == "one"


@tile_config
def test_tile_master_and_slave(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    assert manager.c.layout.info()["master"] == ["three"]
    assert manager.c.layout.info()["slave"] == ["two", "one"]

    manager.c.next_layout()
    assert manager.c.layout.info()["master"] == ["three", "two"]
    assert manager.c.layout.info()["slave"] == ["one"]


@tile_config
def test_tile_remove(manager):
    one = manager.test_window("one")
    manager.test_window("two")
    three = manager.test_window("three")

    assert manager.c.layout.info()["master"] == ["three"]
    manager.kill_window(one)
    assert manager.c.layout.info()["master"] == ["three"]
    manager.kill_window(three)
    assert manager.c.layout.info()["master"] == ["two"]


@tile_config
def test_tile_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions, Tile adds (by default) clients at pos of current
    assert manager.c.layout.info()['clients'] == ['three', 'two', 'one']
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, 'two', 'one', 'float1', 'float2', 'three')
