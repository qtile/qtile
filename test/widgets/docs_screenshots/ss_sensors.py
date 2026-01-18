import sys
from importlib import reload

import pytest

from test.widgets.test_sensors import MockPsutil


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import sensors

    reload(sensors)
    yield sensors.ThermalSensor


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"tag_sensor": "NVME"}, {"format": "{tag}: {temp:.0f}{unit}"}, {"threshold": 30.0}],
    indirect=True,
)
def ss_thermal_sensor(screenshot_manager):
    screenshot_manager.take_screenshot()
