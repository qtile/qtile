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

from time import sleep

import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focus_path, assert_focused


class RatioTileConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [layout.RatioTile(ratio=0.5), layout.RatioTile(), layout.RatioTile(fancy=True)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


ratiotile_config = pytest.mark.parametrize("manager", [RatioTileConfig], indirect=True)


@ratiotile_config
def test_ratiotile_add_windows(manager):
    for i in range(12):
        manager.test_window(str(i))
        if i == 0:
            assert manager.c.layout.info()["layout_info"] == [(0, 0, 800, 600)]
        elif i == 1:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 400, 600),
                (400, 0, 400, 600),
            ]
        elif i == 2:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 600),
                (266, 0, 266, 600),
                (532, 0, 268, 600),
            ]
        elif i == 3:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 200, 600),
                (200, 0, 200, 600),
                (400, 0, 200, 600),
                (600, 0, 200, 600),
            ]
        elif i == 4:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 160, 600),
                (160, 0, 160, 600),
                (320, 0, 160, 600),
                (480, 0, 160, 600),
                (640, 0, 160, 600),
            ]
        elif i == 5:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 133, 600),
                (133, 0, 133, 600),
                (266, 0, 133, 600),
                (399, 0, 133, 600),
                (532, 0, 133, 600),
                (665, 0, 135, 600),
            ]
        elif i == 6:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 200, 300),
                (200, 0, 200, 300),
                (400, 0, 200, 300),
                (600, 0, 200, 300),
                (0, 300, 266, 300),
                (266, 300, 266, 300),
                (532, 300, 268, 300),
            ]
        elif i == 7:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 200, 300),
                (200, 0, 200, 300),
                (400, 0, 200, 300),
                (600, 0, 200, 300),
                (0, 300, 200, 300),
                (200, 300, 200, 300),
                (400, 300, 200, 300),
                (600, 300, 200, 300),
            ]
        elif i == 8:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 160, 300),
                (160, 0, 160, 300),
                (320, 0, 160, 300),
                (480, 0, 160, 300),
                (640, 0, 160, 300),
                (0, 300, 200, 300),
                (200, 300, 200, 300),
                (400, 300, 200, 300),
                (600, 300, 200, 300),
            ]
        elif i == 9:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 160, 300),
                (160, 0, 160, 300),
                (320, 0, 160, 300),
                (480, 0, 160, 300),
                (640, 0, 160, 300),
                (0, 300, 160, 300),
                (160, 300, 160, 300),
                (320, 300, 160, 300),
                (480, 300, 160, 300),
                (640, 300, 160, 300),
            ]
        elif i == 10:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 133, 300),
                (133, 0, 133, 300),
                (266, 0, 133, 300),
                (399, 0, 133, 300),
                (532, 0, 133, 300),
                (665, 0, 135, 300),
                (0, 300, 160, 300),
                (160, 300, 160, 300),
                (320, 300, 160, 300),
                (480, 300, 160, 300),
                (640, 300, 160, 300),
            ]
        elif i == 11:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 133, 300),
                (133, 0, 133, 300),
                (266, 0, 133, 300),
                (399, 0, 133, 300),
                (532, 0, 133, 300),
                (665, 0, 135, 300),
                (0, 300, 133, 300),
                (133, 300, 133, 300),
                (266, 300, 133, 300),
                (399, 300, 133, 300),
                (532, 300, 133, 300),
                (665, 300, 135, 300),
            ]
        else:
            assert False


@ratiotile_config
def test_ratiotile_add_windows_golden_ratio(manager):
    manager.c.next_layout()
    for i in range(12):
        manager.test_window(str(i))
        if i == 0:
            assert manager.c.layout.info()["layout_info"] == [(0, 0, 800, 600)]
        elif i == 4:
            # the rest test col order
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 400, 200),
                (0, 200, 400, 200),
                (0, 400, 400, 200),
                (400, 0, 400, 300),
                (400, 300, 400, 300),
            ]
        elif i == 5:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 400, 200),
                (0, 200, 400, 200),
                (0, 400, 400, 200),
                (400, 0, 400, 200),
                (400, 200, 400, 200),
                (400, 400, 400, 200),
            ]

        elif i == 9:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 266, 150),
                (266, 150, 266, 150),
                (266, 300, 266, 150),
                (266, 450, 266, 150),
                (532, 0, 266, 300),
                (532, 300, 266, 300),
            ]
        elif i == 10:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 266, 150),
                (266, 150, 266, 150),
                (266, 300, 266, 150),
                (266, 450, 266, 150),
                (532, 0, 266, 200),
                (532, 200, 266, 200),
                (532, 400, 266, 200),
            ]
        elif i == 11:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 266, 150),
                (266, 150, 266, 150),
                (266, 300, 266, 150),
                (266, 450, 266, 150),
                (532, 0, 266, 150),
                (532, 150, 266, 150),
                (532, 300, 266, 150),
                (532, 450, 266, 150),
            ]


@ratiotile_config
def test_ratiotile_basic(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    sleep(0.1)
    assert manager.c.window.info()["width"] == 264
    assert manager.c.window.info()["height"] == 598
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["name"] == "three"

    manager.c.group.next_window()
    assert manager.c.window.info()["width"] == 264
    assert manager.c.window.info()["height"] == 598
    assert manager.c.window.info()["x"] == 266
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["name"] == "two"

    manager.c.group.next_window()
    assert manager.c.window.info()["width"] == 266
    assert manager.c.window.info()["height"] == 598
    assert manager.c.window.info()["x"] == 532
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["name"] == "one"


@ratiotile_config
def test_ratiotile_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions, RatioTile adds clients to head
    assert manager.c.layout.info()["clients"] == ["three", "two", "one"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "two", "one", "float1", "float2", "three")


@ratiotile_config
def test_ratiotile_alternative_calculation(manager):
    manager.c.next_layout()
    manager.c.next_layout()

    for i in range(12):
        manager.test_window(str(i))
        print(manager.c.layout.info()["layout_info"])
        if i == 0:
            assert manager.c.layout.info()["layout_info"] == [(0, 0, 800, 600)]
        elif i == 4:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 400, 200),
                (0, 200, 400, 200),
                (0, 400, 400, 200),
                (400, 0, 400, 300),
                (400, 300, 400, 300),
            ]
        elif i == 5:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 400, 200),
                (0, 200, 400, 200),
                (0, 400, 400, 200),
                (400, 0, 400, 200),
                (400, 200, 400, 200),
                (400, 400, 400, 200),
            ]
        elif i == 9:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 267, 200),
                (266, 200, 267, 200),
                (266, 400, 267, 200),
                (533, 0, 267, 200),
                (533, 200, 267, 200),
                (533, 400, 267, 200),
            ]
        elif i == 10:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 267, 150),
                (266, 150, 267, 150),
                (266, 300, 267, 150),
                (266, 450, 267, 150),
                (533, 0, 267, 200),
                (533, 200, 267, 200),
                (533, 400, 267, 200),
            ]
        elif i == 11:
            assert manager.c.layout.info()["layout_info"] == [
                (0, 0, 266, 150),
                (0, 150, 266, 150),
                (0, 300, 266, 150),
                (0, 450, 266, 150),
                (266, 0, 267, 150),
                (266, 150, 267, 150),
                (266, 300, 267, 150),
                (266, 450, 267, 150),
                (533, 0, 267, 150),
                (533, 150, 267, 150),
                (533, 300, 267, 150),
                (533, 450, 267, 150),
            ]


@ratiotile_config
def test_shuffling(manager):
    def clients():
        return manager.c.layout.info()["clients"]

    for i in range(3):
        manager.test_window(str(i))

    assert clients() == ["2", "1", "0"]
    manager.c.layout.shuffle_up()
    assert clients() == ["0", "2", "1"]
    manager.c.layout.shuffle_up()
    assert clients() == ["1", "0", "2"]
    manager.c.layout.shuffle_down()
    assert clients() == ["0", "2", "1"]
    manager.c.layout.shuffle_down()
    assert clients() == ["2", "1", "0"]


@ratiotile_config
def test_resizing(manager):
    def sizes():
        return manager.c.layout.info()["layout_info"]

    for i in range(5):
        manager.test_window(str(i))

    assert sizes() == [
        (0, 0, 160, 600),
        (160, 0, 160, 600),
        (320, 0, 160, 600),
        (480, 0, 160, 600),
        (640, 0, 160, 600),
    ]

    manager.c.layout.increase_ratio()
    assert sizes() == [
        (0, 0, 266, 300),
        (266, 0, 266, 300),
        (532, 0, 268, 300),
        (0, 300, 400, 300),
        (400, 300, 400, 300),
    ]

    manager.c.layout.decrease_ratio()
    assert sizes() == [
        (0, 0, 160, 600),
        (160, 0, 160, 600),
        (320, 0, 160, 600),
        (480, 0, 160, 600),
        (640, 0, 160, 600),
    ]
