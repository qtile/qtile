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


def custom_text_parser(name):
    return f"TEST-{name}-TEST"


class WindowTabsConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
    layouts = [layout.Stack()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    fake_screens = [
        Screen(
            top=bar.Bar(
                [
                    widget.WindowTabs(),
                    widget.WindowTabs(name="customparse", parse_text=custom_text_parser),
                ],
                24,
            ),
            bottom=bar.Bar(
                [
                    widget.WindowTabs(selected="!!"),
                ],
                24,
            ),
            x=0,
            y=0,
            width=900,
            height=960,
        ),
    ]
    screens = []


windowtabs_config = pytest.mark.parametrize("manager", [WindowTabsConfig], indirect=True)


@windowtabs_config
def test_single_window_states(manager):
    def widget_text():
        return manager.c.bar["top"].info()["widgets"][0]["text"]

    # When no windows are spawned the text should be ""
    # Initially TextBox has " " but the Config.set_group function already
    # calls focus_change hook, so the text should be updated to ""
    assert widget_text() == ""

    # Load a window
    proc = manager.test_window("one")
    assert widget_text() == "<b>one</b>"

    # Maximize window
    manager.c.window.toggle_maximize()
    assert widget_text() == "<b>[] one</b>"

    # Minimize window
    manager.c.window.toggle_minimize()
    assert widget_text() == "<b>_ one</b>"

    # Float window
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_floating()
    assert widget_text() == "<b>V one</b>"

    # Kill the window and check empty string again
    manager.kill_window(proc)
    assert widget_text() == ""


@windowtabs_config
def test_multiple_windows(manager):
    def widget_text():
        return manager.c.bar["top"].info()["widgets"][0]["text"]

    window_one = manager.test_window("one")
    assert widget_text() == "<b>one</b>"

    window_two = manager.test_window("two")
    assert widget_text() in ["<b>two</b> | one", "one | <b>two</b>"]

    manager.c.layout.next()
    assert widget_text() in ["<b>one</b> | two", "two | <b>one</b>"]

    manager.kill_window(window_one)
    assert widget_text() == "<b>two</b>"

    manager.kill_window(window_two)
    assert widget_text() == ""


@windowtabs_config
def test_selected(manager):
    # Bottom bar widget has custom "selected" indicator
    def widget_text():
        return manager.c.bar["bottom"].info()["widgets"][0]["text"]

    window_one = manager.test_window("one")
    assert widget_text() == "!!one!!"

    manager.kill_window(window_one)
    assert widget_text() == ""


@windowtabs_config
def test_escaping_text(manager):
    """
    Ampersands can cause a crash if not escaped before passing to
    pangocffi.parse_markup.
    Test that the widget can parse text safely.
    """
    manager.test_window("Text & Text")
    assert manager.c.widget["windowtabs"].info()["text"] == "<b>Text &amp; Text</b>"


@windowtabs_config
def test_custom_text_parser(manager):
    """Test the custom text parser function."""
    manager.test_window("one")
    assert manager.c.widget["customparse"].info()["text"] == "<b>TEST-one-TEST</b>"
