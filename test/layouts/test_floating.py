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
from test.layouts.layout_utils import assert_focused


class FloatingConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [layout.Floating()]
    floating_layout = layout.Floating(
        fullscreen_border_width=15,
        max_border_width=10,
    )
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


floating_config = pytest.mark.parametrize("manager", [FloatingConfig], indirect=True)


@floating_config
def test_float_next_prev_window(manager):
    # spawn three windows
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    # focus previous windows
    assert_focused(manager, "three")
    manager.c.group.prev_window()
    assert_focused(manager, "two")
    manager.c.group.prev_window()
    assert_focused(manager, "one")
    # checking that it loops around properly
    manager.c.group.prev_window()
    assert_focused(manager, "three")

    # focus next windows
    # checking that it loops around properly
    manager.c.group.next_window()
    assert_focused(manager, "one")
    manager.c.group.next_window()
    assert_focused(manager, "two")
    manager.c.group.next_window()
    assert_focused(manager, "three")


@floating_config
def test_border_widths(manager):
    manager.test_window("one")

    # Default geometry
    info = manager.c.window.info()
    assert info["x"] == 350
    assert info["y"] == 250
    assert info["width"] == 100
    assert info["height"] == 100

    # Fullscreen
    manager.c.window.enable_fullscreen()
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == 770
    assert info["height"] == 570
    manager.c.window.disable_fullscreen()

    # Maximized
    manager.c.window.toggle_maximize()
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == 780
    assert info["height"] == 580
