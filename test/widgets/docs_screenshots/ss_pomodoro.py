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
from datetime import timedelta

import pytest

from libqtile.widget import pomodoro
from test.widgets.test_pomodoro import MockDatetime


def increment_time(self, increment):
    MockDatetime._adjustment += timedelta(minutes=increment)


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("libqtile.widget.pomodoro.datetime", MockDatetime)
    pomodoro.Pomodoro.adjust_time = increment_time
    yield pomodoro.Pomodoro


def ss_pomodoro(screenshot_manager):
    bar = screenshot_manager.c.bar["top"]
    widget = screenshot_manager.c.widget["pomodoro"]

    # Inactive
    screenshot_manager.take_screenshot()

    bar.fake_button_press(0, "top", 0, 0, 3)
    widget.eval("self.update(self.poll())")

    # Active
    screenshot_manager.take_screenshot()

    widget.eval("self.adjust_time(25)")
    widget.eval("self.update(self.poll())")

    # Short break
    screenshot_manager.take_screenshot()
