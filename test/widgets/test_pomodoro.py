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
from datetime import datetime, timedelta
from importlib import reload

import pytest

from libqtile.widget import pomodoro
from test.widgets.conftest import FakeBar

COLOR_INACTIVE = "123456"
COLOR_ACTIVE = "654321"
COLOR_BREAK = "AABBCC"
PREFIX_INACTIVE = "TESTING POMODORO"
PREFIX_ACTIVE = "ACTIVE"
PREFIX_BREAK = "BREAK"
PREFIX_LONG_BREAK = "LONG BREAK"
PREFIX_PAUSED = "PAUSING"


# Mock Datetime object that returns a set datetime but can
# be adjusted via the '_adjustment' property
class MockDatetime(datetime):
    _adjustment = timedelta(0)

    @classmethod
    def now(cls, *args, **kwargs):
        return cls(2021, 1, 1, 12, 00, 0) + cls._adjustment


@pytest.fixture
def patched_widget(monkeypatch):
    reload(pomodoro)
    monkeypatch.setattr("libqtile.widget.pomodoro.datetime", MockDatetime)
    yield pomodoro


@pytest.mark.usefixtures("patched_widget")
def test_pomodoro(fake_qtile, fake_window):
    widget = pomodoro.Pomodoro(
        update_interval=100,
        color_active=COLOR_ACTIVE,
        color_inactive=COLOR_INACTIVE,
        color_break=COLOR_BREAK,
        num_pomodori=2,
        length_pomodori=15,
        length_short_break=5,
        length_long_break=10,
        notification_on=False,
        prefix_inactive=PREFIX_INACTIVE,
        prefix_active=PREFIX_ACTIVE,
        prefix_break=PREFIX_BREAK,
        prefix_long_break=PREFIX_LONG_BREAK,
        prefix_paused=PREFIX_PAUSED,
    )

    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)

    # When we start, widget is inactive
    assert widget.poll() == PREFIX_INACTIVE
    assert widget.layout.colour == COLOR_INACTIVE

    # Left clicking toggles state
    widget._toggle_break()
    assert widget.poll() == f"{PREFIX_ACTIVE}0:15:0"
    assert widget.layout.colour == COLOR_ACTIVE

    # Another left click should pause
    widget._toggle_break()
    assert widget.poll() == PREFIX_PAUSED
    assert widget.layout.colour == COLOR_INACTIVE

    widget._toggle_break()
    # Add 5 mins should take 5 mins off our timer
    MockDatetime._adjustment += timedelta(minutes=5)
    assert widget.poll() == f"{PREFIX_ACTIVE}0:10:0"
    assert widget.layout.colour == COLOR_ACTIVE

    # Add 10 mins should take us to end of first pomodoro
    # So we get a short break between pomodori
    MockDatetime._adjustment += timedelta(minutes=10)
    assert widget.poll() == f"{PREFIX_BREAK}0:5:0"
    assert widget.layout.colour == COLOR_BREAK

    # Add 5 mins should take us to start of second pomodoro
    MockDatetime._adjustment += timedelta(minutes=5)
    assert widget.poll() == f"{PREFIX_ACTIVE}0:15:0"
    assert widget.layout.colour == COLOR_ACTIVE

    # Add 15 mins should take us to end of second pomodoro
    # and start of long break (as there are only two pomodori)
    MockDatetime._adjustment += timedelta(minutes=15)
    assert widget.poll() == f"{PREFIX_LONG_BREAK}0:10:0"
    assert widget.layout.colour == COLOR_BREAK

    # Move forward so we're at start of next pomodoro
    MockDatetime._adjustment += timedelta(minutes=10)
    assert widget.poll() == f"{PREFIX_ACTIVE}0:15:0"

    # Advance into pomodoro
    MockDatetime._adjustment += timedelta(minutes=10)
    assert widget.poll() == f"{PREFIX_ACTIVE}0:5:0"

    # Right-click toggles active state
    widget._toggle_active()
    assert widget.poll() == PREFIX_INACTIVE

    # Right-click again resets status
    widget._toggle_active()
    assert widget.poll() == f"{PREFIX_ACTIVE}0:15:0"
