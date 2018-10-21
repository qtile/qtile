# Copyright (c) 2018 Shunsuke Mie
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

from . import base


class DirtyMemory(base._TextBox):
    """
        This widget show a dirty memory size.
        You can guess the current status of disk write by this value.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_delay', 5, 'The delay in seconds between updates'),
        ('show_format', 'DirtyMemory: {}', 'A text format in bar'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "Dirty", **config)
        self.add_defaults(DirtyMemory.defaults)
        self.last_value = 0

    def timer_setup(self):
        self.update()
        self.timeout_add(self.update_delay, self.timer_setup)

    def _get_current(self):
        with open('/proc/meminfo') as file:
            for line in file:
                tmp = line.rstrip().split(':')
                if tmp[0] == 'Dirty':
                    return tmp[1].lstrip()

    def update(self):
        current_value = self._get_current()
        if current_value != self.last_value:
            self.text = self.show_format.format(current_value)
            self.bar.draw()
