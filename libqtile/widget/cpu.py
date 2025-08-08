# Copyright (c) 2019 Niko Järvinen (b10011)

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

import psutil

from libqtile.widget import base


class CPU(base.BackgroundPoll):
    """
    A simple widget to display CPU load and frequency.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """

    defaults = [
        ("update_interval", 1.0, "Update interval for the CPU widget"),
        (
            "format",
            "CPU {freq_current}GHz {load_percent}%",
            "CPU display format",
        ),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(CPU.defaults)

    def poll(self):
        variables = dict()

        variables["load_percent"] = round(psutil.cpu_percent(), 1)
        freq = psutil.cpu_freq()
        if psutil.__version__ == "5.9.0":
            variables["freq_current"] = round(freq.current, 1)
        else:
            variables["freq_current"] = round(freq.current / 1000, 1)
        variables["freq_max"] = round(freq.max / 1000, 1)
        variables["freq_min"] = round(freq.min / 1000, 1)

        return self.format.format(**variables)
