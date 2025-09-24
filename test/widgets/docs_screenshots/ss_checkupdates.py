import pytest

import libqtile.widget
from test.widgets.test_check_updates import MockPopen, MockSpawn


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("libqtile.widget.base.subprocess.check_output", MockSpawn.call_process)
    monkeypatch.setattr("libqtile.widget.check_updates.Popen", MockPopen)
    yield libqtile.widget.CheckUpdates


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"no_update_string": "No updates"},
    ],
    indirect=True,
)
def ss_checkupdates(screenshot_manager):
    # First screenshot shows updates available
    screenshot_manager.take_screenshot()

    # Polling mocks updates being installed
    screenshot_manager.c.widget["checkupdates"].eval("self.update(self.poll())")

    # Second screenshot means there are no updates to install
    screenshot_manager.take_screenshot()
