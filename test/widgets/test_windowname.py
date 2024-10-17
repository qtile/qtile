# Copyright (c) 2021 elParaguayo
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

# Widget specific tests

import pytest

import libqtile.config
from libqtile import bar, layout, widget
from libqtile.config import Screen
from libqtile.confreader import Config


class WindowNameConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
    layouts = [layout.Max()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    fake_screens = [
        Screen(
            top=bar.Bar(
                [
                    widget.WindowName(),
                ],
                24,
            ),
            x=0,
            y=0,
            width=900,
            height=480,
        ),
        Screen(
            top=bar.Bar(
                [
                    widget.WindowName(for_current_screen=True),
                ],
                24,
            ),
            x=0,
            y=480,
            width=900,
            height=480,
        ),
    ]
    screens = []


windowname_config = pytest.mark.parametrize("manager", [WindowNameConfig], indirect=True)


@windowname_config
def test_window_names(manager):
    def widget_text_on_screen(index):
        return manager.c.screen[index].bar["top"].info()["widgets"][0]["text"]

    # Screen 1's widget is set up with for_current_screen=True
    # This means that when screen 0 is active, screen 1's widget should show the same text

    assert widget_text_on_screen(0) == " "
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Load a window
    proc = manager.test_window("one")
    assert widget_text_on_screen(0) == "one"
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Maximize window
    manager.c.window.toggle_maximize()
    assert widget_text_on_screen(0) == "[] one"
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Minimize window
    manager.c.window.toggle_minimize()
    assert widget_text_on_screen(0) == "_ one"
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Float window
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_floating()
    assert widget_text_on_screen(0) == "V one"
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Kill the window and check text again
    manager.kill_window(proc)
    assert widget_text_on_screen(0) == " "
    assert widget_text_on_screen(0) == widget_text_on_screen(1)

    # Quick test to check for_current_screen=False works
    manager.c.to_screen(1)
    proc = manager.test_window("one")
    assert widget_text_on_screen(0) == " "
    assert widget_text_on_screen(1) == "one"
    manager.kill_window(proc)
