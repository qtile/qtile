# Copyright (c) 2014 Rock Neurotiko
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

from libqtile.log_utils import logger
from libqtile.widget import base

from typing import List  # noqa: F401


class Net(base.ThreadedPollText):
    """Displays interface down and up speed"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('interface', None, 'List of interfaces to monitor or None to displays all active NICs combined'),
        ('update_interval', 1, 'The update interval.'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Net.defaults)
        if type(self.interface) != list:
            if self.interface == None:
                self.interface = "all"
            self.interface = [self.interface]
        self.stats = self.get_stats()

    def convert_b(self, b):

        letters = ["b", "kb", "Mb", "Gb", "Tb", "Pb", "Eb", "Zb", "Yb"]
        factor = 1000.0
        i = 0

        while int(b / 1000) > 0:
            b /= factor
            i = i + 1

        return b, letters[i]

    def get_stats(self):
        interfaces = {}
        if self.interface == ["all"]:
            net = psutil.net_io_counters(pernic=False)
            interfaces["all"] = {'down': net[1], 'up': net[0]}
            return interfaces
        else:
            net = psutil.net_io_counters(pernic=True)
            for iface in net:
                name = iface
                down = net[iface].bytes_recv
                up = net[iface].bytes_sent
                interfaces[name] = {'down': down, 'up': up}
            return interfaces

    def _format(self, down, up):
        down = "%0.2f" % down
        up = "%0.2f" % up
        if len(down) > 5:
            down = down[:5]
        if len(up) > 5:
            up = up[:5]

        down = " " * (5 - len(down)) + down
        up = " " * (5 - len(up)) + up
        return down, up

    def poll(self):
        try:
            ret_stat = ""
            for intf in self.interface:
                new_stats = self.get_stats()
                down = new_stats[intf]['down'] - \
                    self.stats[intf]['down']
                up = new_stats[intf]['up'] - \
                    self.stats[intf]['up']

                down = down / self.update_interval
                up = up / self.update_interval
                down, down_letter = self.convert_b(down)
                up, up_letter = self.convert_b(up)
                down, up = self._format(down, up)
                str_base = "%s: %s%s \u2193\u2191 %s%s "
                self.stats[intf] = new_stats[intf]
                ret_stat += str_base % (intf, down, down_letter, up, up_letter)

            return ret_stat
        except Exception as excp:
            logger.error('%s: Caught Exception:\n%s',
                         self.__class__.__name__, excp)
