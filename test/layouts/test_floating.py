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
    return no_xinerama(pytest.mark.parametrize("manager", [FloatingConfig], indirect=True)(x))


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
