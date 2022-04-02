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
from test.layouts.layout_utils import assert_focus_path, assert_focused


class BspConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [layout.Bsp(), layout.Bsp(margin_on_single=10)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


bsp_config = pytest.mark.parametrize("manager", [BspConfig], indirect=True)

# This currently only tests the window focus cycle


@bsp_config
def test_bsp_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions, columns adds clients at pos of current, in two stacks
    assert manager.c.layout.info()["clients"] == ["one", "three", "two"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "two", "float1", "float2", "one", "three")


@bsp_config
def test_bsp_margin_on_single(manager):
    manager.test_window("one")

    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0

    manager.c.next_layout()
    info = manager.c.window.info()
    assert info["x"] == 10
    assert info["y"] == 10

    manager.test_window("two")
    # No longer single window so margin reverts to "margin" which is 0
    info = manager.c.window.info()
    assert info["x"] == 0
