import sys
from importlib import reload

import pytest

from test.widgets.test_memory import FakePsutil


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", FakePsutil("psutil"))
    from libqtile.widget import memory

    reload(memory)
    return memory.Memory


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"measure_mem": "G"},
        {"format": "Swap: {SwapUsed: .0f}{ms}/{SwapTotal: .0f}{ms}"},
    ],
    indirect=True,
)
def ss_memory(screenshot_manager):
    screenshot_manager.take_screenshot()
