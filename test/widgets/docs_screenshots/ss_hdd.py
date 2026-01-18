import sys
import tempfile
from importlib import reload

import pytest

from test.widgets.test_hdd import MockPsutil, set_io_ticks


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import hdd

    reload(hdd)
    yield hdd.HDD


def ss_cpu(screenshot_manager):
    # Create a fake stat file
    temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    widget = screenshot_manager.c.widget["hdd"]
    widget.eval(f"self.path = '{temp_file.name}'")

    set_io_ticks(temp_file, 0)
    widget.eval("self.update(self.poll())")

    set_io_ticks(temp_file, 123000)
    widget.eval("self.update(self.poll())")

    screenshot_manager.take_screenshot()
