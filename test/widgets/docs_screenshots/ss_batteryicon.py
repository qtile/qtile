import pytest

import libqtile.widget
import libqtile.widget.battery
from libqtile.widget.battery import BatteryState, BatteryStatus
from test.widgets.test_battery import dummy_load_battery


@pytest.fixture
def widget(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.DISCHARGING,
        percent=0.5,
        power=15.0,
        time=1729,
        charge_start_threshold=0,
        charge_end_threshold=100,
    )

    monkeypatch.setattr("libqtile.widget.battery.load_battery", dummy_load_battery(loaded_bat))
    yield libqtile.widget.battery.BatteryIcon


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_batteryicon(screenshot_manager):
    screenshot_manager.take_screenshot()
