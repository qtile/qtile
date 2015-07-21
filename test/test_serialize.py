# Copyright (c) 2015 Aniruddh Kanojia
# Copyright (c) 2015 Sean Vig
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

import libqtile
import libqtile.layout
import libqtile.bar
import libqtile.command
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.hook
import libqtile.confreader

from nose.plugins.attrib import attr

from .utils import Xephyr


class LayoutTestConfig(object):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
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

    def __init__(self, layout):
        self.layouts = [
            layout
        ]


passing_layouts = [
    libqtile.layout.Tile(),
    libqtile.layout.Max(),
    libqtile.layout.RatioTile(),
    libqtile.layout.Matrix(),
    libqtile.layout.MonadTall(),
    libqtile.layout.Stack(),
    libqtile.layout.Zoomy(),
    libqtile.layout.VerticalTile(),
    libqtile.layout.Slice('left', 256, wname='slice')
]

broken_layouts = [
    libqtile.layout.TreeTab(),
]


@attr('xephyr')
def simple_serialization_tests():
    for layout in passing_layouts:
        @Xephyr(True, LayoutTestConfig(layout))
        def test_serialize_simple(self):
            self.testWindow("one")
            self.testWindow("two")
            self.testWindow("three")
            a = self.c.get_info()
            self.simulate_restart()
            b = self.c.get_info()
            assert a == b
        yield test_serialize_simple


@attr('xephyr')
def change_focus_serialization_tests():
    for layout in passing_layouts:
        @Xephyr(True, LayoutTestConfig(layout))
        def test_serialize_change_focus(self):
            self.testWindow("one")
            self.testWindow("two")
            self.testWindow("three")
            self.c.group.next_window()
            a = self.c.get_info()
            self.simulate_restart()
            b = self.c.get_info()
            assert a == b

            self.c.group.next_window()
            a = self.c.get_info()
            self.simulate_restart()
            b = self.c.get_info()
            assert a == b

            self.c.group.next_window()
            a = self.c.get_info()
            self.simulate_restart()
            b = self.c.get_info()
            assert a == b
        yield test_serialize_change_focus
