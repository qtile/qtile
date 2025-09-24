import sys
from importlib import reload

import pytest

from test.widgets.test_load import MockPsutil


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import load

    reload(load)
    yield load.Load


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"format": "{time}: {load:.1f}"}], indirect=True
)
def ss_load(screenshot_manager):
    screenshot_manager.take_screenshot()
