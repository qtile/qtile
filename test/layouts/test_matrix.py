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

class MatrixConfig(object):
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


matrix_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [MatrixConfig], indirect=True)(x))


@matrix_config
def test_matrix_simple(qtile):
    qtile.testWindow("one")
    assert qtile.c.layout.info()["rows"] == [["one"]]
    qtile.testWindow("two")
    assert qtile.c.layout.info()["rows"] == [["one", "two"]]
    qtile.testWindow("three")
    assert qtile.c.layout.info()["rows"] == [["one", "two"], ["three"]]


@matrix_config
def test_matrix_navigation(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    qtile.testWindow("four")
    qtile.testWindow("five")
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
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    qtile.testWindow("four")
    qtile.testWindow("five")
    qtile.c.layout.add()
    assert qtile.c.layout.info()["rows"] == [["one", "two", "three"], ["four", "five"]]
    qtile.c.layout.delete()
    assert qtile.c.layout.info()["rows"] == [["one", "two"], ["three", "four"], ["five"]]


@matrix_config
def test_matrix_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("float1")
    qtile.c.window.toggle_floating()
    qtile.testWindow("float2")
    qtile.c.window.toggle_floating()
    qtile.testWindow("three")

    # test preconditions
    assert qtile.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assertFocused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assertFocusPath(qtile, 'float1', 'float2', 'one', 'two', 'three')
