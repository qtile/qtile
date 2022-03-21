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
import pytest

import libqtile.widget


@pytest.fixture
def widget(monkeypatch):
    yield libqtile.widget.WidgetBox


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"widgets": [libqtile.widget.TextBox("Widget inside box.")]},
    ],
    indirect=True,
)
def ss_widgetbox(screenshot_manager):
    bar = screenshot_manager.c.bar["top"]

    # We can't just take a picture of the widget. We also need the area of the bar
    # that is revealed when the box is open.
    # As there are no other widgets here, we can just add up the length of all widgets.
    def bar_width():
        info = bar.info()
        widgets = info["widgets"]
        if not widgets:
            return 0

        return sum(x["length"] for x in widgets)

    def take_screenshot():
        target = screenshot_manager.target()
        bar.take_screenshot(target, width=bar_width())

    # Box is closed to start with
    take_screenshot()

    # Open the box to show contents
    screenshot_manager.c.widget["widgetbox"].toggle()
    take_screenshot()
