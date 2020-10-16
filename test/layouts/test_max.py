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
    return no_xinerama(pytest.mark.parametrize("qtile", [MaxConfig], indirect=True)(x))


class MaxLayeredConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Max(only_focused=False)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


def maxlayered_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MaxLayeredConfig], indirect=True)(x))


@max_config
def test_max_simple(qtile):
    qtile.test_window("one")
    assert qtile.c.layout.info()["clients"] == ["one"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0))]
    qtile.test_window("two")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 1))]


@maxlayered_config
def test_layered_max_simple(qtile):
    qtile.test_window("one")
    assert qtile.c.layout.info()["clients"] == ["one"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0))]
    qtile.test_window("two")
    assert qtile.c.layout.info()["clients"] == ["one", "two"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 1))]


@max_config
def test_max_updown(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("three")
    assert qtile.c.layout.info()["clients"] == ["one", "two", "three"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 0)), ("three", (0, 0, 0, 0, 2))]
    qtile.c.layout.up()
    assert qtile.c.groups()["a"]["focus"] == "two"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 2)), ("three", (0, 0, 0, 0, 0))]
    qtile.c.layout.down()
    assert qtile.c.groups()["a"]["focus"] == "three"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 0)), ("three", (0, 0, 0, 0, 2))]


@maxlayered_config
def test_layered_max_updown(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("three")
    assert qtile.c.layout.info()["clients"] == ["one", "two", "three"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 1)), ("three", (0, 0, 0, 0, 2))]
    qtile.c.layout.up()
    assert qtile.c.groups()["a"]["focus"] == "two"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 1)), ("two", (0, 0, 0, 0, 2)), ("three", (0, 0, 0, 0, 0))]
    qtile.c.layout.up()
    assert qtile.c.groups()["a"]["focus"] == "one"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 2)), ("two", (0, 0, 0, 0, 0)), ("three", (0, 0, 0, 0, 1))]
    qtile.c.layout.down()
    assert qtile.c.groups()["a"]["focus"] == "two"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 1)), ("two", (0, 0, 0, 0, 2)), ("three", (0, 0, 0, 0, 0))]
    qtile.c.layout.down()
    assert qtile.c.groups()["a"]["focus"] == "three"
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 1)), ("three", (0, 0, 0, 0, 2))]


def max_remove(qtile):
    qtile.test_window("one")
    two = qtile.test_window("two")
    assert qtile.c.layout.info()["clients"] == ["one", "two"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0)), ("two", (0, 0, 0, 0, 1))]
    qtile.kill_window(two)
    assert qtile.c.layout.info()["clients"] == ["one"]
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == [("one", (0, 0, 0, 0, 0))]


@max_config
def test_max_remove(qtile):
    max_remove(qtile)


@maxlayered_config
def test_layered_max_remove(qtile):
    max_remove(qtile)


@max_config
def test_max_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("float1")
    qtile.c.window.toggle_floating()
    qtile.test_window("float2")
    qtile.c.window.toggle_floating()
    qtile.test_window("three")

    # test preconditions
    assert qtile.c.layout.info()['clients'] == ['one', 'two', 'three']
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 0)), ('float1', (0, 0, 0, 1, 0)),
            ('float2', (0, 0, 0, 1, 1)), ('three', (0, 0, 0, 0, 2))]
    # last added window has focus
    assert_focused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(qtile, 'float1', 'float2', 'one', 'two', 'three')


@maxlayered_config
def test_layered_max_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("float1")
    qtile.c.window.toggle_floating()
    qtile.test_window("float2")
    qtile.c.window.toggle_floating()
    qtile.test_window("three")

    # test preconditions
    assert qtile.c.layout.info()['clients'] == ['one', 'two', 'three']
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('float1', (0, 0, 0, 1, 0)),
            ('float2', (0, 0, 0, 1, 1)), ('three', (0, 0, 0, 0, 2))]
    # last added window has focus
    assert_focused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(qtile, 'float1', 'float2', 'one', 'two', 'three')
