# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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
from test.layouts.layout_utils import assert_focused


class FloatingConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [
        layout.Floating()
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def floating_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [FloatingConfig], indirect=True)(x))


@floating_config
def test_float_next_prev_window(qtile):
    self = qtile

    # spawn three windows
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")

    # focus previous windows
    assert_focused(self, "three")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
    self.c.group.prev_window()
    assert_focused(self, "two")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
    self.c.group.prev_window()
    assert_focused(self, "one")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
    # checking that it loops around properly
    self.c.group.prev_window()
    assert_focused(self, "three")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]

    # focus next windows
    # checking that it loops around properly
    self.c.group.next_window()
    assert_focused(self, "one")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
    self.c.group.next_window()
    assert_focused(self, "two")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
    self.c.group.next_window()
    assert_focused(self, "three")
    assert [(w["name"], w["z"]) for w in qtile.c.windows()] == \
           [('one', (0, 0, 0, 0, 0)), ('two', (0, 0, 0, 0, 1)), ('three', (0, 0, 0, 0, 2))]
