import pytest

from libqtile.widget import nvidia_sensors
from test.widgets.test_nvidia_sensors import MockNvidiaSMI


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr(MockNvidiaSMI, "temperature", "65")
    monkeypatch.setattr(
        nvidia_sensors.NvidiaSensors, "call_process", MockNvidiaSMI.get_temperature
    )
    yield nvidia_sensors.NvidiaSensors


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"threshold": 60, "foreground_alert": "ff6000"}], indirect=True
)
def ss_nvidia_sensors(screenshot_manager):
    screenshot_manager.take_screenshot()
