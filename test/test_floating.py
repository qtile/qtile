# Copyright (c) 2023 Yonnji
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
from libqtile import bar, layout, widget
from libqtile.config import Screen
from libqtile.confreader import Config


class FakeScreenConfig(Config):
    auto_fullscreen = True
    floating_layout = layout.Floating()
    groups = [
        libqtile.config.Group(
            "a",
            layouts=[floating_layout],
        ),
    ]
    layouts = [
        layout.Tile(),
    ]
    keys = []
    mouse = []
    fake_screens = [
        Screen(
            top=bar.Bar(
                [widget.GroupBox(), widget.WindowName(), widget.Clock()],
                10,
            ),
            width=1920,
            height=1080,
        ),
    ]
    screens = []


fakescreen_config = pytest.mark.parametrize("manager", [FakeScreenConfig], indirect=True)


@fakescreen_config
def test_maximize(manager):
    """Ensure that maximize saves and restores geometry"""
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["width"] == 1920
    assert manager.c.window.info()["height"] == 1070
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 10
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"


@fakescreen_config
def test_fullscreen(manager):
    """Ensure that fullscreen saves and restores geometry"""
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["width"] == 1920
    assert manager.c.window.info()["height"] == 1080
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"
