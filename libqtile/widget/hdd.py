# Copyright (c) 2024 Florian G. Hechler

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from libqtile.widget import base


class HDD(base.BackgroundPoll):
    """
    Displays HDD usage in percent based on the number of milliseconds the device has been performing I/O operations.
    """

    defaults = [
        ("device", "sda", "Block device to monitor (e.g. sda)"),
        (
            "format",
            "HDD {HDDPercent}%",
            "HDD display format",
        ),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(HDD.defaults)
        self.path = f"/sys/block/{self.device}/stat"
        self._prev = 0

    def poll(self):
        variables = dict()
        # Field index 9 contains the number of milliseconds the device has been performing I/O operations
        with open(self.path) as f:
            io_ticks = int(f.read().split()[9])

        variables["HDDPercent"] = round(
            max(min(((io_ticks - self._prev) / self.update_interval) / 10, 100.0), 0.0), 1
        )

        self._prev = io_ticks

        return self.format.format(**variables)
