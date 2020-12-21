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


class MatrixConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Matrix(columns=2)
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


def matrix_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MatrixConfig], indirect=True)(x))


@matrix_config
def test_matrix_simple(self):
    self.test_window("one")
    assert self.c.layout.info()["rows"] == [["one"]]
    self.test_window("two")
    assert self.c.layout.info()["rows"] == [["one", "two"]]
    self.test_window("three")
    assert self.c.layout.info()["rows"] == [["one", "two"], ["three"]]


@matrix_config
def test_matrix_navigation(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    self.test_window("four")
    self.test_window("five")
    self.c.layout.right()
    assert self.c.layout.info()["current_window"] == (0, 2)
    self.c.layout.up()
    assert self.c.layout.info()["current_window"] == (0, 1)
    self.c.layout.up()
    assert self.c.layout.info()["current_window"] == (0, 0)
    self.c.layout.up()
    assert self.c.layout.info()["current_window"] == (0, 2)
    self.c.layout.down()
    assert self.c.layout.info()["current_window"] == (0, 0)
    self.c.layout.down()
    assert self.c.layout.info()["current_window"] == (0, 1)
    self.c.layout.right()
    assert self.c.layout.info()["current_window"] == (1, 1)
    self.c.layout.right()
    assert self.c.layout.info()["current_window"] == (0, 1)


@matrix_config
def test_matrix_add_remove_columns(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    self.test_window("four")
    self.test_window("five")
    self.c.layout.add()
    assert self.c.layout.info()["rows"] == [["one", "two", "three"], ["four", "five"]]
    self.c.layout.delete()
    assert self.c.layout.info()["rows"] == [["one", "two"], ["three", "four"], ["five"]]


@matrix_config
def test_matrix_window_focus_cycle(self):
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


@matrix_config
def test_matrix_next_no_clients(self):
    self.c.layout.next()


@matrix_config
def test_matrix_previous_no_clients(self):
    self.c.layout.previous()
