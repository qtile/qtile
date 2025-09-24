import sys
from importlib import reload

import pytest

from test.widgets.test_wlan import MockIwlib


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "iwlib", MockIwlib("iwlib"))
    from libqtile.widget import wlan

    reload(wlan)
    yield wlan.Wlan


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"format": "{essid} {percent:2.0%}"}], indirect=True
)
def ss_wlan(screenshot_manager):
    screenshot_manager.take_screenshot()
