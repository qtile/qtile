# -*- coding: utf-8 -*-
# Copyright (c) 2015 Tycho Andersen
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

# Widget specific tests

import pytest
from libqtile.config import Screen
from libqtile.bar import Bar
from libqtile.widget import TextBox, ThermalSensor
from ..conftest import BareConfig

class ColorChanger(TextBox):
    count = 0

    def update(self, text):
        self.count += 1
        if self.count % 2 == 0:
            self.foreground = "ff0000"
        else:
            self.foreground = "0000ff"
        self.text = text


class WidgetTestConf(BareConfig):
    screens = [Screen(bottom=Bar([ColorChanger(name="colorchanger")], 20))]


widget_conf = pytest.mark.parametrize("qtile", [WidgetTestConf], indirect=True)

@widget_conf
def test_textbox_color_change(qtile):
    qtile.c.widget["colorchanger"].update('f')
    assert qtile.c.widget["colorchanger"].info()["foreground"] == "0000ff"

    qtile.c.widget["colorchanger"].update('f')
    assert qtile.c.widget["colorchanger"].info()["foreground"] == "ff0000"


def test_thermalsensor_regex_compatibility():
    sensors = ThermalSensor()
    test_sensors_output = """
    coretemp-isa-0000
    Adapter: ISA adapter
    Physical id 0:  +61.0°C  (high = +86.0°C, crit = +100.0°C)
    Core 0:         +54.0°C  (high = +86.0°C, crit = +100.0°C)
    Core 1:         +56.0°C  (high = +86.0°C, crit = +100.0°C)
    Core 2:         +58.0°C  (high = +86.0°C, crit = +100.0°C)
    Core 3:         +61.0°C  (high = +86.0°C, crit = +100.0°C)
    """
    sensors_detected = sensors._format_sensors_output(test_sensors_output)
    assert sensors_detected["Physical id 0"] == ("61.0", "°C")
    assert sensors_detected["Core 0"] == ("54.0", "°C")
    assert sensors_detected["Core 1"] == ("56.0", "°C")
    assert sensors_detected["Core 2"] == ("58.0", "°C")
    assert sensors_detected["Core 3"] == ("61.0", "°C")
    assert not ("Adapter" in sensors_detected.keys())
