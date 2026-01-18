import sys
from importlib import reload

import pytest

from test.widgets.test_cpu import MockPsutil


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import cpu

    reload(cpu)
    yield cpu.CPU


def ss_cpu(screenshot_manager):
    screenshot_manager.take_screenshot()
