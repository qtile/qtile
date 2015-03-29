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
from . import base

BACKLIGHT_DIR = '/sys/class/backlight'

FORMAT = '{percent: 2.0%}'


class Backlight(base.InLoopPollText):
    """
        A simple widget to show the current brightness of a monitor.
    """

    filenames = {}

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
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Backlight.defaults)

    def _load_file(self, name):
        try:
            path = os.path.join(BACKLIGHT_DIR, self.backlight_name, name)
            with open(path, 'r') as f:
                return f.read().strip()
        except IOError:
            return False
        except Exception:
            self.log.exception("Failed to get %s" % name)

    def _get_info(self):
        try:
            info = {
                'brightness': float(self._load_file(self.brightness_file)),
                'max': float(self._load_file(self.max_brightness_file)),
            }
        except TypeError:
            return False
        return info

    def poll(self):
        info = self._get_info()
        if info is False:
            return 'Error'

        percent = info['brightness'] / info['max']
        return FORMAT.format(percent=percent)
