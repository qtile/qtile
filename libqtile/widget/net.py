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

from __future__ import annotations

from math import log

import psutil

from libqtile.log_utils import logger
from libqtile.widget import base


class Net(base.BackgroundPoll):
    """
    Displays interface down and up speed

    The following fields are available in the `format` string:

    - ``interface``: name of the interface
    - ``down``: download speed
    - ``down_suffix``: suffix for the download speed
    - ``down_cumulative``: cumulative download traffic
    - ``down_cumulative_suffix``: suffix for the cumulative download traffic
    - ``up``: upload speed
    - ``up_suffix``: suffix for the upload speed
    - ``up_cumulative``: cumulative upload traffic
    - ``up_cumulative_suffix``: suffix for the cumulative upload traffic
    - ``total``: total speed
    - ``total_suffix``: suffix for the total speed
    - ``total_cumulative``: cumulative total traffic
    - ``total_cumulative_suffix``: suffix for the cumulative total traffic

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """

    defaults = [
        (
            "format",
            "{interface}: {down:6.2f}{down_suffix:<2}\u2193\u2191{up:6.2f}{up_suffix:<2}",
            "Display format of down/upload/total speed of given interfaces",
        ),
        (
            "interface",
            None,
            "List of interfaces or single NIC as string to monitor, \
            None to display all active NICs combined",
        ),
        ("update_interval", 1, "The update interval."),
        ("use_bits", False, "Use bits instead of bytes per second?"),
        ("prefix", None, "Use a specific prefix for the unit of the speed."),
        (
            "cumulative_prefix",
            None,
            "Use a specific prefix for the unit of the cumulative traffic.",
        ),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(Net.defaults)

        self.factor = 1000.0
        self.allowed_prefixes = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]

        if self.use_bits:
            self.base_unit = "b"
            self.byte_multiplier = 8
        else:
            self.base_unit = "B"
            self.byte_multiplier = 1

        self.units = list(map(lambda p: p + self.base_unit, self.allowed_prefixes))

        if not isinstance(self.interface, list):
            if self.interface is None:
                self.interface = ["all"]
            elif isinstance(self.interface, str):
                self.interface = [self.interface]
            else:
                raise AttributeError(
                    f"Invalid Argument passed: {self.interface}\nAllowed Types: list, str, None"
                )
        self.stats = self.get_stats()

    def convert_b(self, num_bytes: float, prefix: str | None = None) -> tuple[float, str]:
        """Converts the number of bytes to the correct unit"""

        num_bytes *= self.byte_multiplier

        if prefix is None:
            if num_bytes > 0:
                power = int(log(num_bytes) / log(self.factor))
                power = min(power, len(self.units) - 1)
            else:
                power = 0
        else:
            power = self.allowed_prefixes.index(prefix)

        converted_bytes = num_bytes / self.factor**power
        unit = self.units[power]

        return converted_bytes, unit

    def get_stats(self):
        interfaces = {}
        if self.interface == ["all"]:
            net = psutil.net_io_counters(pernic=False)
            interfaces["all"] = {
                "down": net.bytes_recv,
                "up": net.bytes_sent,
                "total": net.bytes_recv + net.bytes_sent,
            }
            return interfaces
        else:
            net = psutil.net_io_counters(pernic=True)
            for iface in net:
                down = net[iface].bytes_recv
                up = net[iface].bytes_sent
                interfaces[iface] = {
                    "down": down,
                    "up": up,
                    "total": down + up,
                }
            return interfaces

    def poll(self):
        ret_stat = []
        try:
            new_stats = self.get_stats()
            for intf in self.interface:
                down = new_stats[intf]["down"] - self.stats[intf]["down"]
                up = new_stats[intf]["up"] - self.stats[intf]["up"]
                total = new_stats[intf]["total"] - self.stats[intf]["total"]

                down = down / self.update_interval
                up = up / self.update_interval
                total = total / self.update_interval
                down, down_suffix = self.convert_b(down, self.prefix)
                down_cumulative, down_cumulative_suffix = self.convert_b(
                    new_stats[intf]["down"], self.cumulative_prefix
                )
                up, up_suffix = self.convert_b(up, self.prefix)
                up_cumulative, up_cumulative_suffix = self.convert_b(
                    new_stats[intf]["up"], self.cumulative_prefix
                )
                total, total_suffix = self.convert_b(total, self.prefix)
                total_cumulative, total_cumulative_suffix = self.convert_b(
                    new_stats[intf]["total"], self.cumulative_prefix
                )
                self.stats[intf] = new_stats[intf]
                ret_stat.append(
                    self.format.format(
                        interface=intf,
                        down=down,
                        down_suffix=down_suffix,
                        down_cumulative=down_cumulative,
                        down_cumulative_suffix=down_cumulative_suffix,
                        up=up,
                        up_suffix=up_suffix,
                        up_cumulative=up_cumulative,
                        up_cumulative_suffix=up_cumulative_suffix,
                        total=total,
                        total_suffix=total_suffix,
                        total_cumulative=total_cumulative,
                        total_cumulative_suffix=total_cumulative_suffix,
                    )
                )

            return " ".join(ret_stat)
        except Exception:
            logger.exception("Net widget errored while polling:")
