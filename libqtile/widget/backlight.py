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
from typing import Dict

from libqtile.log_utils import logger
from libqtile.widget import base

BACKLIGHT_DIR = '/sys/class/backlight'


class Backlight(base.InLoopPollText):
    """A simple widget to show the current brightness of a monitor.

    If the change_command parameter is set to None, the widget will attempt to
    use the interface at /sys/class to change brightness. Depending on the
    setup, the user may need to be added to the video group to have permission
    to write to this interface. This depends on having the correct udev rules
    the brightness file; these are typically installed alongside brightness
    tools such as brightnessctl (which changes the group to 'video') so
    installing that is an easy way to get it working.
    """

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
        ('change_command', 'xbacklight -set {0}', 'Execute command to change value')
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Backlight.defaults)
        self.future = None

        self.brightness_file = os.path.join(
            BACKLIGHT_DIR, self.backlight_name, self.brightness_file,
        )
        self.max_brightness_file = os.path.join(
            BACKLIGHT_DIR, self.backlight_name, self.max_brightness_file,
        )
        self.max_value = self._load_file(self.max_brightness_file)
        self.step = self.max_value * self.step / 100

    def _load_file(self, path):
        try:
            with open(path, 'r') as f:
                return float(f.read().strip())
        except FileNotFoundError:
            logger.debug('Failed to get %s' % path)
            raise RuntimeError(
                'Unable to read status for {}'.format(os.path.basename(path))
            )

    def _get_info(self):
        brightness = self._load_file(self.brightness_file)

        info = {
            'brightness': brightness,
            'max': self.max_value,
        }
        return info

    def poll(self):
        try:
            info = self._get_info()
        except RuntimeError as e:
            return 'Error: {}'.format(e)

        percent = info['brightness'] / info['max']
        return self.format.format(percent=percent)

    def change_backlight(self, value):
        if self.change_command is None:
            try:
                with open(self.brightness_file, 'w') as f:
                    f.write(str(round(value)))
            except PermissionError:
                logger.warning("Cannot set brightness: no write permission for {0}"
                               .format(self.brightness_file))
        else:
            self.call_process(shlex.split(self.change_command.format(value)))

    def button_press(self, x, y, button):
        if self.future and not self.future.done():
            return
        info = self._get_info()
        if not info:
            new = now = self.max_value
        else:
            new = now = info["brightness"]
        if button == 5:  # down
            new = max(now - self.step, 0)
        elif button == 4:  # up
            new = min(now + self.step, self.max_value)
        if new != now:
            self.future = self.qtile.run_in_executor(self.change_backlight,
                                                     new)
