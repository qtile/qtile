# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2012, 2014 Craig Barnes
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

from liblavinder.widget import base


class She(base.InLoopPollText):
    """Widget to display the Super Hybrid Engine status

    Can display either the mode or CPU speed on eeepc computers.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('device', '/sys/devices/platform/eeepc/cpufv', 'sys path to cpufv'),
        ('format', 'speed', 'Type of info to display "speed" or "name"'),
        ('update_interval', 0.5, 'Update Time in seconds.'),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(She.defaults)
        self.modes = {
            '0x300': {'name': 'Performance', 'speed': '1.6GHz'},
            '0x301': {'name': 'Normal', 'speed': '1.2GHz'},
            '0x302': {'name': 'PoswerSave', 'speed': '800MHz'}
        }

    def poll(self):
        with open(self.device) as f:
            mode = f.read().strip()
        if mode in self.modes:
            return self.modes[mode][self.format]
        else:
            return mode
