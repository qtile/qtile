# Copyright (c) 2022 elParaguayo
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
from libqtile.confreader import Config


class ScreenSplitConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.Max(), layout.ScreenSplit()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = [
        libqtile.config.Screen(
            top=bar.Bar(
                [widget.ScreenSplit(), widget.ScreenSplit(format="{layout} - {split_name}")], 40
            )
        )
    ]
    follow_mouse_focus = False


screensplit_config = pytest.mark.parametrize("manager", [ScreenSplitConfig], indirect=True)


@screensplit_config
def test_screensplit_text(manager):
    widget = manager.c.widget["screensplit"]
    assert widget.info()["text"] == ""

    manager.c.next_layout()
    assert widget.info()["text"] == "top (max)"

    manager.c.layout.next_split()
    assert widget.info()["text"] == "bottom (columns)"

    manager.c.next_layout()
    assert widget.info()["text"] == ""


@screensplit_config
def test_screensplit_scroll_actions(manager):
    widget = manager.c.widget["screensplit"]
    bar = manager.c.bar["top"]

    assert widget.info()["text"] == ""

    manager.c.next_layout()
    assert widget.info()["text"] == "top (max)"

    bar.fake_button_press(0, "top", 0, 0, 4)
    assert widget.info()["text"] == "bottom (columns)"

    bar.fake_button_press(0, "top", 0, 0, 4)
    assert widget.info()["text"] == "top (max)"

    bar.fake_button_press(0, "top", 0, 0, 5)
    assert widget.info()["text"] == "bottom (columns)"

    bar.fake_button_press(0, "top", 0, 0, 5)
    assert widget.info()["text"] == "top (max)"


@screensplit_config
def test_screensplit_text_format(manager):
    widget = manager.c.widget["screensplit_1"]
    manager.c.next_layout()
    assert widget.info()["text"] == "max - top"
