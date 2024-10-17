# Copyright (c) 2022 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class Temp:
    def __init__(self, label, temp, fahrenheit=False):
        self.label = label
        self.current = temp
        if fahrenheit:
            self.current = (self.current * 9 / 5) + 32


class MockPsutil(ModuleType):
    @classmethod
    def sensors_temperatures(cls, fahrenheit=False):
        return {"core": [Temp("CPU", 45.0, fahrenheit)], "nvme": [Temp("NVME", 56.3, fahrenheit)]}


@pytest.fixture
def sensors_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen, request):
    params = getattr(request, "param", dict())
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import sensors

    reload(sensors)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([sensors.ThermalSensor(**params)], 10))]

    if "set_defaults" in params:
        config.widget_defaults = {"foreground": "123456"}

    manager_nospawn.start(config)
    yield manager_nospawn


def test_thermal_sensor_metric(sensors_manager):
    assert sensors_manager.c.widget["thermalsensor"].info()["text"] == "45.0°C"


@pytest.mark.parametrize("sensors_manager", [{"metric": False}], indirect=True)
def test_thermal_sensor_imperial(sensors_manager):
    assert sensors_manager.c.widget["thermalsensor"].info()["text"] == "113.0°F"


@pytest.mark.parametrize("sensors_manager", [{"tag_sensor": "NVME"}], indirect=True)
def test_thermal_sensor_tagged_sensor(sensors_manager):
    assert sensors_manager.c.widget["thermalsensor"].info()["text"] == "56.3°C"


@pytest.mark.parametrize("sensors_manager", [{"tag_sensor": "does_not_exist"}], indirect=True)
def test_thermal_sensor_unknown_sensor(sensors_manager):
    assert sensors_manager.c.widget["thermalsensor"].info()["text"] == "N/A"


@pytest.mark.parametrize(
    "sensors_manager", [{"format": "{tag}: {temp:.0f}{unit}"}], indirect=True
)
def test_thermal_sensor_format(sensors_manager):
    assert sensors_manager.c.widget["thermalsensor"].info()["text"] == "CPU: 45°C"


def test_thermal_sensor_colour_normal(sensors_manager):
    _, temp = sensors_manager.c.widget["thermalsensor"].eval("self.layout.colour")
    assert temp == "ffffff"


@pytest.mark.parametrize("sensors_manager", [{"threshold": 30}], indirect=True)
def test_thermal_sensor_colour_alert(sensors_manager):
    _, temp = sensors_manager.c.widget["thermalsensor"].eval("self.layout.colour")
    assert temp == "ff0000"


@pytest.mark.parametrize("sensors_manager", [{"set_defaults": True}], indirect=True)
def test_thermal_sensor_widget_defaults(sensors_manager):
    _, temp = sensors_manager.c.widget["thermalsensor"].eval("self.layout.colour")
    assert temp == "123456"
