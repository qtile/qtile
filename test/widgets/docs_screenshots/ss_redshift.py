# Copyright (c) 2024 Saath Satheeshkumar (saths008)
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
from test.widgets.test_redshift import mock_run


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("subprocess.run", mock_run)
    yield libqtile.widget.redshift.Redshift


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_redshift(screenshot_manager):
    def click():
        screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)

    w = screenshot_manager.c.widget["redshift"]

    screenshot_manager.take_screenshot()

    click()  # Enable so scrolling works

    number_of_items = 4
    for _ in range(number_of_items):
        screenshot_manager.take_screenshot()
        w.scroll_up()
