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

import psutil

from libqtile.widget import base


class ThermalSensor(base.InLoopPollText):
    """Widget to display temperature sensor information

    For using the thermal sensor widget you need to have lm-sensors installed.
    You can get a list of the tag_sensors executing "sensors" in your terminal.
    Then you can choose which you want, otherwise it will display the first
    available.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """
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

    def get_temp_sensors(self):
        """
        Reads temperatures from sys-fs via psutil.
        Output will be read Fahrenheit if user has specified it to be.
        """

        temperature_list = {}
        temps = psutil.sensors_temperatures(fahrenheit=not self.metric)
        unit = '°C' if self.metric else '°F'
        empty_index = 0
        for kernel_module in temps:
            for sensor in temps[kernel_module]:
                label = sensor.label
                if not label:
                    label = "{}-{}".format(kernel_module if kernel_module else 'UNKNOWN', str(empty_index))
                    empty_index += 1
                temperature_list[label] = (str(round(sensor.current, 1)), unit)

        return temperature_list

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
