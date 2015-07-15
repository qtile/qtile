# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Sebastien Blot
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

import os
import time
import subprocess
import signal
import libqtile
import libqtile.layout
import libqtile.bar
import libqtile.command
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.hook
import libqtile.confreader

import nose
from nose.tools import assert_raises
from nose.plugins.attrib import attr

from . import utils
from .utils import Xephyr


class TestConfig:
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
                libqtile.layout.Tile(),
                libqtile.layout.Max(),
                libqtile.layout.RatioTile(),
                libqtile.layout.Matrix(),
                libqtile.layout.MonadTall(),
                libqtile.layout.Stack(),
                libqtile.layout.Zoomy(),
                libqtile.layout.VerticalTile(),
                libqtile.layout.TreeTab(),
                # libqtile.layout.Slice('left', 256, wname= 'google'),

            ]
    floating_layout = libqtile.layout.floating.Floating(
        float_rules=[dict(wmclass="xclock")])
    keys = [
        libqtile.config.Key(
            ["control"],
            "k",
            libqtile.command._Call([("layout", None)], "up")
        ),
        libqtile.config.Key(
            ["control"],
            "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
    ]
    mouse = []
    screens = [libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.widget.GroupBox(),
                        ],
                        20
                    ),
    )]
    main = None
    follow_mouse_focus = True


@Xephyr(True, TestConfig())
def test_minimal(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    a = self.c.get_info()
    x = self.simulate_restart()
    b = self.c.get_info()
    assert a == b


@Xephyr(True, TestConfig())
def test_move(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    self.c.group.next_window()
    a = self.c.get_info()
    x = self.simulate_restart()
    b = self.c.get_info()
    print(a),'\n\n'
    print(b)
    assert a == b

    self.c.group.next_window()
    a = self.c.get_info()
    x = self.simulate_restart()
    b = self.c.get_info()
    assert a == b

    self.c.group.next_window()
    a = self.c.get_info()
    x = self.simulate_restart()
    b = self.c.get_info()
    assert a == b
