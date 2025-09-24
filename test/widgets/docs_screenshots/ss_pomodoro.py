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

    bar.fake_button_press(0, 0, 3)
    widget.eval("self.update(self.poll())")

    # Active
    screenshot_manager.take_screenshot()

    widget.eval("self.adjust_time(25)")
    widget.eval("self.update(self.poll())")

    # Short break
    screenshot_manager.take_screenshot()
