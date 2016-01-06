# vim: tabstop=4 shiftwidth=4 expandtab
# -*- coding:utf-8 -*-
# Copyright (c) 2012 TiN
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Foster McLane
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
#
# coding: utf-8

import re

from six import u, PY2

from . import base
from ..utils import UnixCommandNotFound, catch_exception_and_warn


class ThermalSensor(base.InLoopPollText):
    '''
    For using the thermal sensor widget you need to have lm-sensors installed.
    You can get a list of the tag_sensors executing "sensors" in your terminal.
    Then you can choose which you want, otherwise it will display the first
    available.
    '''
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('metric', True, 'True to use metric/C, False to use imperial/F'),
        ('show_tag', False, 'Show tag sensor'),
        ('update_interval', 2, 'Update interval in seconds'),
        ('tag_sensor', None,
            'Tag of the temperature sensor. For example: "temp1" or "Core 0"'),
        (
            'threshold',
            70,
            'If the current temperature value is above, '
            'then change to foreground_alert colour'
        ),
        ('foreground_alert', 'ff0000', 'Foreground colour alert'),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(ThermalSensor.defaults)
        self.sensors_temp = re.compile(
            u(r"""
            ([\w ]+):   # Sensor tag name
            \s+[+|-]    # temp signed
            (\d+\.\d+)  # temp value
            ({degrees}  # ° match
            [C|F])      # Celsius or Fahrenheit
            """.format(degrees="\xc2\xb0" if PY2 else "\xb0")),
            re.UNICODE | re.VERBOSE
        )
        self.value_temp = re.compile("\d+\.\d+")
        temp_values = self.get_temp_sensors()
        self.foreground_normal = self.foreground

        if temp_values is None:
            self.data = "sensors command not found"
        elif len(temp_values) == 0:
            self.data = "Temperature sensors not found"
        elif self.tag_sensor is None:
            for k in temp_values:
                self.tag_sensor = k
                break

    @catch_exception_and_warn(warning=UnixCommandNotFound, excepts=OSError)
    def get_temp_sensors(self):
        """calls the unix `sensors` command with `-f` flag if user has specified that
        the output should be read in Fahrenheit.
        """
        command = ["sensors", ]
        if not self.metric:
            command.append("-f")
        sensors_out = self.call_process(command)
        return self._format_sensors_output(sensors_out)

    def _format_sensors_output(self, sensors_out):
        """formats output of unix `sensors` command into a dict of
        {<sensor_name>: (<temperature>, <temperature symbol>), ..etc..}
        """
        temperature_values = {}
        for name, temp, symbol in self.sensors_temp.findall(sensors_out):
            name = name.strip()
            temperature_values[name] = temp, symbol
        return temperature_values

    def poll(self):
        temp_values = self.get_temp_sensors()
        if temp_values is None:
            return False
        text = ""
        if self.show_tag and self.tag_sensor is not None:
            text = self.tag_sensor + ": "
        text += "".join(temp_values.get(self.tag_sensor, ['N/A']))
        temp_value = float(temp_values.get(self.tag_sensor, [0])[0])
        if temp_value > self.threshold:
            self.layout.colour = self.foreground_alert
        else:
            self.layout.colour = self.foreground_normal
        return text
