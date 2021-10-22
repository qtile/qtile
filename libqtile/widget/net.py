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
from math import log
from typing import Tuple

import psutil

from libqtile.log_utils import logger
from libqtile.widget import base


class Net(base.ThreadPoolText):
    """
    Displays interface down and up speed


    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('format', '{interface}: {down} \u2193\u2191 {up}',
         'Display format of down/upload/total speed and down_size/up_size of given interfaces'),
        ('interface', None, 'List of interfaces or single NIC as string to monitor, \
            None to displays all active NICs combined'),
        ('update_interval', 1, 'The update interval.'),
        ('use_bits', False, 'Use bits instead of bytes per second?'),
        ('factor', 1000, 'Factor to calculate bytes, allowed is 1000 for ex. kB and 1024 for ex kiB),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Net.defaults)
        if not isinstance(self.interface, list):
            if self.interface is None:
                self.interface = ["all"]
            elif isinstance(self.interface, str):
                self.interface = [self.interface]
            else:
                raise AttributeError("Invalid Argument passed: %s\nAllowed Types: List, String, None" % self.interface)

        if self.factor not in [1000, 1024]:
            raise AttributeError("Invalid Argument passed: %s\nAllowed value: 1000, 1024" % self.factor)

        self.stats = self.get_stats()
            
    def convert_b(self, num_bytes: float) -> Tuple[float, str]:
        """Converts the number of bytes to the correct unit"""
        factor = self.factor

        if self.use_bits:
            letters = ["b", "kb", "Mb", "Gb", "Tb", "Pb", "Eb", "Zb", "Yb"]
            num_bytes *= 8
        else:
            letters = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]            

        if num_bytes > 0:
            power = int(log(num_bytes) / log(factor))
            power = max(min(power, len(letters) - 1), 0)
        else:
            power = 0

        converted_bytes = num_bytes / factor**power
        unit = letters[power]

        if factor == 1024 and len(unit) > 1:
            unit = unit[:1] + "i" + unit[1:]

        return converted_bytes, unit

    def get_stats(self):
        interfaces = {}
        print(time.time())
        if self.interface == ["all"]:
            net = psutil.net_io_counters(pernic=False)
            interfaces["all"] = {
                    'down': net.bytes_recv,
                    'up': net.bytes_sent,
                    'total': net.bytes_recv + net.bytes_sent,
                }
            return interfaces
        else:
            net = psutil.net_io_counters(pernic=True)
            for iface in net:
                down = net[iface].bytes_recv
                up = net[iface].bytes_sent
                interfaces[iface] = {
                        'down': down,
                        'up': up,
                        'total': down + up,
                    }
            return interfaces

    def _format(self, down, down_letter, up, up_letter, total, total_letter, size_down, size_down_letter, size_up, size_up_letter):
        if self.factor == 1000:
            value_size = 7
        else:
            value_size = 8

        max_len_down = value_size - len(down_letter)
        max_len_up = value_size - len(up_letter)
        max_len_total = value_size - len(total_letter)
        max_len_down_size = value_size - len(size_down_letter)
        max_len_up_size = value_size - len(size_up_letter)
        down = '{val:{max_len}.2f}'.format(val=down, max_len=max_len_down)
        up = '{val:{max_len}.2f}'.format(val=up, max_len=max_len_up)
        total = '{val:{max_len}.2f}'.format(val=total, max_len=max_len_total)
        size_down = '{val:{max_len}.2f}'.format(val=size_down, max_len=max_len_down_size)
        size_up = '{val:{max_len}.2f}'.format(val=size_up, max_len=max_len_up_size)
        return down[:max_len_down], up[:max_len_up], total[:max_len_total], size_down[:max_len_down_size], size_up[:max_len_up_size]

    def poll(self):
        ret_stat = []
        try:
            new_stats = self.get_stats()
            for intf in self.interface:
                down = new_stats[intf]['down'] - \
                    self.stats[intf]['down']
                up = new_stats[intf]['up'] - \
                    self.stats[intf]['up']
                total = new_stats[intf]['total'] - \
                    self.stats[intf]['total']

                down = down / self.update_interval
                up = up / self.update_interval
                total = total / self.update_interval
                size_down = new_stats[intf]['down'] 
                size_up = new_stats[intf]['up']
                down, down_letter = self.convert_b(down)
                up, up_letter = self.convert_b(up)
                total, total_letter = self.convert_b(total)
                size_down, size_down_letter = self.convert_b(size_down)
                size_up, size_up_letter = self.convert_b(size_up)
                down, up, total, size_down, size_up  = self._format(
                        down, down_letter,
                        up, up_letter,
                        total, total_letter,
                        size_down, size_down_letter,
                        size_up, size_up_letter
                    )
                self.stats[intf] = new_stats[intf]
                ret_stat.append(
                    self.format.format(
                        **{
                            'interface': intf,
                            'down': down + down_letter,
                            'up': up + up_letter,
                            'total': total + total_letter,
                            'size_down': size_down + size_down_letter,
                            'size_up': size_up + size_up_letter
                        }))

            return " ".join(ret_stat)
        except Exception as excp:
            logger.error('%s: Caught Exception:\n%s',
                         self.__class__.__name__, excp)
