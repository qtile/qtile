# Copyright (c) 2012 Tim Neumann
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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

import os
import shlex
from . import base

try:
    from typing import Dict  # noqa: F401
except ImportError:
    pass

BACKLIGHT_DIR = '/sys/class/backlight'


class Backlight(base.InLoopPollText):
    """A simple widget to show the current brightness of a monitor"""

    filenames = {}  # type: Dict

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ('backlight_name', 'acpi_video0', 'ACPI name of a backlight device'),
        (
            'brightness_file',
            'brightness',
            'Name of file with the '
            'current brightness in /sys/class/backlight/backlight_name'
        ),
        (
            'max_brightness_file',
            'max_brightness',
            'Name of file with the '
            'maximum brightness in /sys/class/backlight/backlight_name'
        ),
        ('update_interval', .2, 'The delay in seconds between updates'),
        ('step', 10, 'Percent of backlight every scroll changed'),
        ('format', '{percent: 2.0%}', 'Display format'),
        ('change_command', 'xbacklight -set %s', 'Execute command to change value')
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Backlight.defaults)
        self.future = None

    def _load_file(self, name):
        path = os.path.join(BACKLIGHT_DIR, self.backlight_name, name)
        with open(path, 'r') as f:
            return f.read().strip()

    def _get_info(self):
        info = {
            'brightness': float(self._load_file(self.brightness_file)),
            'max': float(self._load_file(self.max_brightness_file)),
        }
        return info

    def poll(self):
        info = self._get_info()
        if not info:
            return 'Error'

        percent = info['brightness'] / info['max']
        return self.format.format(percent=percent)

    def change_backlight(self, value):
        self.call_process(shlex.split(self.change_command % value))

    def button_press(self, x, y, button):
        if self.future and not self.future.done():
            return
        info = self._get_info()
        if info is False:
            new = now = 100
        else:
            new = now = info["brightness"] / info["max"] * 100
        if button == 5:  # down
            new = max(now - self.step, 0)
        elif button == 4:  # up
            new = min(now + self.step, 100)
        if new != now:
            self.future = self.qtile.run_in_executor(self.change_backlight,
                                                     new)
