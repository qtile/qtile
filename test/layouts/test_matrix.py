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
from .layout_utils import assert_focused, assert_focus_path


class MatrixConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Matrix(columns=2)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


def matrix_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MatrixConfig], indirect=True)(x))


@matrix_config
def test_matrix_simple(qtile):
    qtile.test_window("one")
    assert qtile.c.layout.info()["rows"] == [["one"]]
    qtile.test_window("two")
    assert qtile.c.layout.info()["rows"] == [["one", "two"]]
    qtile.test_window("three")
    assert qtile.c.layout.info()["rows"] == [["one", "two"], ["three"]]


@matrix_config
def test_matrix_navigation(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("three")
    qtile.test_window("four")
    qtile.test_window("five")
    qtile.c.layout.right()
    assert qtile.c.layout.info()["current_window"] == (0, 2)
    qtile.c.layout.up()
    assert qtile.c.layout.info()["current_window"] == (0, 1)
    qtile.c.layout.up()
    assert qtile.c.layout.info()["current_window"] == (0, 0)
    qtile.c.layout.up()
    assert qtile.c.layout.info()["current_window"] == (0, 2)
    qtile.c.layout.down()
    assert qtile.c.layout.info()["current_window"] == (0, 0)
    qtile.c.layout.down()
    assert qtile.c.layout.info()["current_window"] == (0, 1)
    qtile.c.layout.right()
    assert qtile.c.layout.info()["current_window"] == (1, 1)
    qtile.c.layout.right()
    assert qtile.c.layout.info()["current_window"] == (0, 1)


@matrix_config
def test_matrix_add_remove_columns(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("three")
    qtile.test_window("four")
    qtile.test_window("five")
    qtile.c.layout.add()
    assert qtile.c.layout.info()["rows"] == [["one", "two", "three"], ["four", "five"]]
    qtile.c.layout.delete()
    assert qtile.c.layout.info()["rows"] == [["one", "two"], ["three", "four"], ["five"]]


@matrix_config
def test_matrix_window_focus_cycle(qtile):
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
    # last added window has focus
    assert_focused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(qtile, 'float1', 'float2', 'one', 'two', 'three')


@matrix_config
def test_matrix_next_no_clients(qtile):
    qtile.c.layout.next()


@matrix_config
def test_matrix_previous_no_clients(qtile):
    qtile.c.layout.previous()
