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
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused


class VerticalTileConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [layout.VerticalTile(columns=2)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


verticaltile_config = pytest.mark.parametrize("manager", [VerticalTileConfig], indirect=True)

class VerticalTileMarginsConfig(VerticalTileConfig):
    layouts = [layout.VerticalTile(), layout.VerticalTile(single_margin=10)]

verticaltile_margins_config = pytest.mark.parametrize("manager", [VerticalTileMarginsConfig], indirect=True)

class VerticalTileBordersConfig(VerticalTileConfig):
    layouts = [layout.VerticalTile(), layout.VerticalTile(single_border_width=10)]

verticaltile_borders_config = pytest.mark.parametrize("manager", [VerticalTileBordersConfig], indirect=True)


@verticaltile_config
def test_verticaltile_simple(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 800, 600)
    manager.test_window("two")
    assert_dimensions(manager, 0, 300, 798, 298)
    manager.test_window("three")
    assert_dimensions(manager, 0, 400, 798, 198)


@verticaltile_config
def test_verticaltile_maximize(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 800, 600)
    manager.test_window("two")
    assert_dimensions(manager, 0, 300, 798, 298)
    # Maximize the bottom layout, taking 75% of space
    manager.c.layout.maximize()
    assert_dimensions(manager, 0, 150, 798, 448)


@verticaltile_config
def test_verticaltile_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions
    assert manager.c.layout.info()["clients"] == ["one", "two", "three"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "float1", "float2", "one", "two", "three")

@verticaltile_margins_config
def test_verticaltile_single_margin(manager):
    manager.test_window("one")

    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0

    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["x"] == 10
    assert info["y"] == 10

    manager.test_window("two")
    # No longer single window so margin reverts to "margin" which is 0
    info = manager.c.window.info()
    assert info["x"] == 0

@verticaltile_borders_config
def test_verticaltile_single_border(manager):
    manager.test_window("one")

    info = manager.c.window.info()
    assert info["width"] == 800
    assert info["height"] == 600

    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["width"] == 780
    assert info["height"] == 580

    manager.test_window("two")
    info = manager.c.window.info()
    assert info["width"] == 798
    assert info["height"] == 298
