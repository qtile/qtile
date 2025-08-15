import pytest

from libqtile.widget.nvidia_sensors import NvidiaSensors, _all_sensors_names_correct
from test.widgets.conftest import FakeBar


def test_nvidia_sensors_input_regex():
    correct_sensors = NvidiaSensors(
        format="temp:{temp}°C,fan{fan_speed}asd,performance{perf}fds"
    )._parse_format_string()
    incorrect_sensors = {"tem", "fan_speed", "perf"}
    assert correct_sensors == {"temp", "fan_speed", "perf"}
    assert _all_sensors_names_correct(correct_sensors)
    assert not _all_sensors_names_correct(incorrect_sensors)


class MockNvidiaSMI:
    # nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader
    # outputs one number for temperature with one gpu.
    temperature = "20"

    @classmethod
    def get_temperature(cls, *args, **kwargs):
        return cls.temperature


@pytest.fixture
def fake_nvidia(fake_qtile, monkeypatch, fake_window):
    n = NvidiaSensors()
    # Replace internal call_process since we cant rely
    # on the test computer having the required hardware.
    monkeypatch.setattr(n, "call_process", MockNvidiaSMI.get_temperature)
    fakebar = FakeBar([n], window=fake_window)
    n._configure(fake_qtile, fakebar)
    return n


def test_nvidia_sensors_foreground_colour(fake_nvidia):
    # Initial temperature
    fake_nvidia.poll()
    assert fake_nvidia.layout.colour == fake_nvidia.foreground_normal

    # Simulate GPU overheating
    MockNvidiaSMI.temperature = "90"
    fake_nvidia.poll()
    assert fake_nvidia.layout.colour == fake_nvidia.foreground_alert

    # And cooling back down
    MockNvidiaSMI.temperature = "20"
    fake_nvidia.poll()
    assert fake_nvidia.layout.colour == fake_nvidia.foreground_normal
