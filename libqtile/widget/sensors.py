#!/usr/bin/env python
# coding: utf-8

from .. import bar, manager
import base
from subprocess import Popen, PIPE
import re


class ThermalSensor(base._TextBox):
    '''
    For using the thermal sensor widget you need to have lm-sensors installed.
    You can get a list of the tag_sensors executing "sensors" in your terminal.
    Then you can choose which you want, otherwise it will display the first
    available.
    '''
    defaults = manager.Defaults(
        ('font', 'Arial', 'Font'),
        ('fontsize', None, 'Pixel size, calculated if None.'),
        ('padding', None, 'Padding, calculated if None.'),
        ('background', '000000', 'Background colour'),
        ('foreground', 'ffffff', 'Foreground colour'),

        ('metric', True, 'True to use metric/C, False to use imperial/F'),
        ('show_tag', False, 'Show tag sensor'),
        ('update_interval', 2, 'Update interval in seconds'),
        ('tag_sensor', None, 'Tag of the temperature sensor'),
        ('threshold', 70, 'If the current temperature value is above, '\
         'then change to foreground_alert colour'),
        ('foreground_alert', 'ff0000', 'Foreground colour alert'),
    )
    def __init__(self, **config):
        base._TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)
        self.sensors_temp = re.compile(
            ur"""
            ([a-zA-Z]+        #Tag
            \s?[0-9]+):       #Tag number
            \s+[+-]           #Temp signed
            ([0-9]+\.[0-9]+)  #Temp value
            (\xc2\xb0         #° match
            [CF])             #Celsius or Fahrenheit
            """,
            re.UNICODE | re.VERBOSE)
        self.value_temp = re.compile("[0-9]+\.[0-9]+")
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

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_interval, self.update)

    def click(self, x, y, button):
        self.update()

    def get_temp_sensors(self):
        fahrenheit = []
        if not self.metric:
            fahrenheit = ["-f"]
        try:
            cmd_sensors = Popen(["sensors",] + fahrenheit, stdout=PIPE)
        except OSError:
            return None
        cmd_sensors.wait()
        (stdout, stderr) = cmd_sensors.communicate()
        temp_values = {}
        for value in re.findall(self.sensors_temp, stdout):
            temp_values[value[0]] = value[1:]
        return temp_values

    def update(self):
        temp_values = self.get_temp_sensors()
        if temp_values is not None:
            self.text = ""
            if self.show_tag and self.tag_sensor is not None:
                self.text = self.tag_sensor + ": "
            self.text += "".join(temp_values.get(self.tag_sensor, ['N/A']))
            temp_value = float(temp_values.get(self.tag_sensor, [0])[0])
            if temp_value > self.threshold:
                self.layout.colour = self.foreground_alert
            else:
                self.layout.colour = self.foreground_normal
            self.bar.draw()
            return True
        else:
            return False
