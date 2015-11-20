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


class TileConfig:
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


@Xephyr(False, TileConfig())
def test_tile_updown(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]
    self.c.layout.down()
    assert self.c.layout.info()["clients"] == ["two", "one", "three"]
    self.c.layout.up()
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]


@Xephyr(False, TileConfig())
def test_tile_nextprev(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")

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


@Xephyr(False, TileConfig())
def test_tile_master_and_slave(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")

    assert self.c.layout.info()["master"] == ["three"]
    assert self.c.layout.info()["slave"] == ["two", "one"]

    self.c.next_layout()
    assert self.c.layout.info()["master"] == ["three", "two"]
    assert self.c.layout.info()["slave"] == ["one"]


@Xephyr(False, TileConfig())
def test_tile_remove(self):
    one = self.testWindow("one")
    self.testWindow("two")
    three = self.testWindow("three")

    assert self.c.layout.info()["master"] == ["three"]
    self.kill(one)
    assert self.c.layout.info()["master"] == ["three"]
    self.kill(three)
    assert self.c.layout.info()["master"] == ["two"]
