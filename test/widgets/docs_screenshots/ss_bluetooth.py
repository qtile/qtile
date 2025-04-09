# Copyright (c) 2023 elParaguayo
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

from test.widgets.test_bluetooth import fake_dbus_daemon, wait_for_text, widget  # noqa: F401


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_bluetooth(fake_dbus_daemon, screenshot_manager):  # noqa: F811
    w = screenshot_manager.c.widget["bluetooth"]
    wait_for_text(w, "BT Speaker")
    screenshot_manager.take_screenshot()

    for _ in range(4):
        w.scroll_up()
        screenshot_manager.take_screenshot()
