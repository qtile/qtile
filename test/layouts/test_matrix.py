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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..utils import Xephyr


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


@Xephyr(False, MatrixConfig())
def test_matrix_simple(self):
    self.testWindow("one")
    assert self.c.layout.info()["rows"] == [["one"]]
    self.testWindow("two")
    assert self.c.layout.info()["rows"] == [["one", "two"]]
    self.testWindow("three")
    assert self.c.layout.info()["rows"] == [["one", "two"],
                                            ["three"]]


@Xephyr(False, MatrixConfig())
def test_matrix_navigation(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    self.testWindow("four")
    self.testWindow("five")
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


@Xephyr(False, MatrixConfig())
def test_matrix_add_remove_columns(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    self.testWindow("four")
    self.testWindow("five")
    self.c.layout.add()
    assert self.c.layout.info()["rows"] == [["one", "two", "three"],
                                            ["four", "five"]]
    self.c.layout.delete()
    assert self.c.layout.info()["rows"] == [["one", "two"],
                                            ["three", "four"],
                                            ["five"]]
