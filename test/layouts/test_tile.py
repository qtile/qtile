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

class TileConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Tile(),
        layout.Tile(masterWindows=2)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


tile_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [TileConfig], indirect=True)(x))


@tile_config
def test_tile_updown(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    assert qtile.c.layout.info()["clients"] == ["three", "two", "one"]
    qtile.c.layout.down()
    assert qtile.c.layout.info()["clients"] == ["two", "one", "three"]
    qtile.c.layout.up()
    assert qtile.c.layout.info()["clients"] == ["three", "two", "one"]


@tile_config
def test_tile_nextprev(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")

    assert qtile.c.layout.info()["clients"] == ["three", "two", "one"]
    assert qtile.c.groups()["a"]["focus"] == "three"

    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "two"

    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] == "three"

    qtile.c.layout.previous()
    assert qtile.c.groups()["a"]["focus"] == "one"

    qtile.c.layout.next()
    qtile.c.layout.next()
    qtile.c.layout.next()
    assert qtile.c.groups()["a"]["focus"] == "one"


@tile_config
def test_tile_master_and_slave(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")

    assert qtile.c.layout.info()["master"] == ["three"]
    assert qtile.c.layout.info()["slave"] == ["two", "one"]

    qtile.c.next_layout()
    assert qtile.c.layout.info()["master"] == ["three", "two"]
    assert qtile.c.layout.info()["slave"] == ["one"]


@tile_config
def test_tile_remove(qtile):
    one = qtile.testWindow("one")
    qtile.testWindow("two")
    three = qtile.testWindow("three")

    assert qtile.c.layout.info()["master"] == ["three"]
    qtile.kill_window(one)
    assert qtile.c.layout.info()["master"] == ["three"]
    qtile.kill_window(three)
    assert qtile.c.layout.info()["master"] == ["two"]

@tile_config
def test_tile_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("float1")
    qtile.c.window.toggle_floating()
    qtile.testWindow("float2")
    qtile.c.window.toggle_floating()
    qtile.testWindow("three")

    # test preconditions, Tile adds (by default) clients at pos of current
    assert qtile.c.layout.info()['clients'] == ['three', 'two', 'one']
    # last added window has focus
    assertFocused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assertFocusPath(qtile, 'two', 'one', 'float1', 'float2', 'three')
