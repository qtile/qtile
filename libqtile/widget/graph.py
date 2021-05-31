# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2010-2011 Paul Colomiets
# Copyright (c) 2010, 2014 roger
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2012 Mika Fischer
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2013 dequis
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Mickael FALCK
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Florian Scherf
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

import itertools
import operator
import time
from os import statvfs

import cairocffi
import psutil

from libqtile.log_utils import logger
from libqtile.widget import base

__all__ = [
    'CPUGraph',
    'MemoryGraph',
    'SwapGraph',
    'NetGraph',
    'HDDGraph',
    'HDDBusyGraph',
]


class _Graph(base._Widget):
    fixed_upper_bound = False
    defaults = [
        ("graph_color", "18BAEB", "Graph color"),
        ("fill_color", "1667EB.3", "Fill color for linefill graph"),
        ("border_color", "215578", "Widget border color"),
        ("border_width", 2, "Widget border width"),
        ("margin_x", 3, "Margin X"),
        ("margin_y", 3, "Margin Y"),
        ("samples", 100, "Count of graph samples."),
        ("frequency", 1, "Update frequency in seconds"),
        ("type", "linefill", "'box', 'line', 'linefill'"),
        ("line_width", 3, "Line width"),
        ("start_pos", "bottom", "Drawer starting position ('bottom'/'top')"),
    ]

    def __init__(self, width=100, **config):
        base._Widget.__init__(self, width, **config)
        self.add_defaults(_Graph.defaults)
        self.values = [0] * self.samples
        self.maxvalue = 0
        self.oldtime = time.time()
        self.lag_cycles = 0

    def _configure(self, qtile, bar):
        super()._configure(qtile, bar)
        if self.type == "box":
            self.drawer.ctx.set_antialias(cairocffi.ANTIALIAS_NONE)

    def timer_setup(self):
        self.timeout_add(self.frequency, self.update)

    @property
    def graphwidth(self):
        return self.width - self.border_width * 2 - self.margin_x * 2

    @property
    def graphheight(self):
        return self.bar.height - self.margin_y * 2 - self.border_width * 2

    def step(self):
        return self.graphwidth / float(self.samples)

    def _for_each_step(self, values):
        for index, val in enumerate(itertools.islice(
            values,
            max(int(-(self.graphwidth / self.step()) + len(values)), 0),
            len(values),
        )):
            yield index, val

    def _prepare_context(self):
        self.drawer.ctx.set_line_join(cairocffi.LINE_JOIN_ROUND)
        if self.graph_color is not None:
            self.drawer.set_source_rgb(self.graph_color)
        self.drawer.ctx.set_line_width(self.line_width)

    def draw_box(self, x, y, values):
        self._prepare_context()
        for _, val in self._for_each_step(values):
            val = self.val(val)
            self.drawer.ctx.rectangle(x, y - val, self.step(), val)
            x += self.step()
        self.drawer.ctx.fill()
        self.drawer.ctx.stroke()

    def draw_line(self, x, y, values):
        self._prepare_context()
        for _, val in self._for_each_step(values):
            self.drawer.ctx.line_to(x, y - self.val(val))
            x += self.step()
        self.drawer.ctx.stroke()

    def draw_linefill(self, x, y, values):
        self._prepare_context()
        for index, val in self._for_each_step(values):
            self.drawer.ctx.line_to(x + index * self.step(), y - self.val(val))
        self.drawer.ctx.stroke_preserve()
        self.drawer.ctx.line_to(
            x + (len(values) - 1) * self.step(),
            y - 1 + self.line_width / 2.0
        )
        self.drawer.ctx.line_to(x, y - 1 + self.line_width / 2.0)
        self.drawer.set_source_rgb(self.fill_color)
        self.drawer.ctx.fill()

    def val(self, val):
        if self.start_pos == 'bottom':
            return val
        elif self.start_pos == 'top':
            return -val
        else:
            raise ValueError("Unknown starting position: %s." % self.start_pos)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        if self.border_width:
            self.drawer.set_source_rgb(self.border_color)
            self.drawer.ctx.set_line_width(self.border_width)
            self.drawer.ctx.rectangle(
                self.margin_x + self.border_width / 2.0,
                self.margin_y + self.border_width / 2.0,
                self.graphwidth + self.border_width,
                self.bar.height - self.margin_y * 2 - self.border_width,
            )
            self.drawer.ctx.stroke()
        x = self.margin_x + self.border_width
        y = self.margin_y + self.border_width
        if self.start_pos == 'bottom':
            y += self.graphheight
        elif not self.start_pos == 'top':
            raise ValueError("Unknown starting position: %s." % self.start_pos)
        k = 1.0 / (self.maxvalue or 1)
        scaled = [self.graphheight * val * k for val in reversed(self.values)]

        if self.type == "box":
            self.draw_box(x, y, scaled)
        elif self.type == "line":
            self.draw_line(x, y, scaled)
        elif self.type == "linefill":
            self.draw_linefill(x, y, scaled)
        else:
            raise ValueError("Unknown graph type: %s." % self.type)

        self.drawer.draw(offsetx=self.offset, width=self.width)

    def push(self, value):
        if self.lag_cycles > self.samples:
            # compensate lag by sending the same value up to
            # the graph samples limit
            self.lag_cycles = 1

        self.values = ([value] * min(self.samples, self.lag_cycles)) + self.values
        self.values = self.values[:self.samples]

        if not self.fixed_upper_bound:
            self.maxvalue = max(self.values)
        self.draw()

    def update(self):
        # lag detection
        newtime = time.time()
        self.lag_cycles = int((newtime - self.oldtime) / self.frequency)
        self.oldtime = newtime

        self.update_graph()
        self.timeout_add(self.frequency, self.update)

    def fulfill(self, value):
        self.values = [value] * len(self.values)


class CPUGraph(_Graph):
    """Display CPU usage graph.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("core", "all", "Which core to show (all/0/1/2/...)"),
    ]

    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(CPUGraph.defaults)
        self.maxvalue = 100
        self.oldvalues = self._getvalues()

    def _getvalues(self):

        if isinstance(self.core, int):
            if self.core > psutil.cpu_count() - 1:
                raise ValueError("No such core: {}".format(self.core))
            cpu = psutil.cpu_times(percpu=True)[self.core]
        else:
            cpu = psutil.cpu_times()

        user = cpu.user * 100
        nice = cpu.nice * 100
        sys = cpu.system * 100
        idle = cpu.idle * 100

        return (int(user), int(nice), int(sys), int(idle))

    def update_graph(self):
        nval = self._getvalues()
        oval = self.oldvalues
        busy = nval[0] + nval[1] + nval[2] - oval[0] - oval[1] - oval[2]
        total = busy + nval[3] - oval[3]
        # sometimes this value is zero for unknown reason (time shift?)
        # we just sent the previous value, because it gives us no info about
        # cpu load, if it's zero.

        if total:
            push_value = busy * 100.0 / total
            self.push(push_value)
        else:
            self.push(self.values[0])
        self.oldvalues = nval


class MemoryGraph(_Graph):
    """Displays a memory usage graph.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """
    orientations = base.ORIENTATION_HORIZONTAL
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        val = self._getvalues()
        self.maxvalue = val['MemTotal']

        mem = val['MemTotal'] - val['MemFree'] - val['Buffers'] - val['Cached']
        self.fulfill(mem)

    def _getvalues(self):
        val = {}
        mem = psutil.virtual_memory()
        val['MemTotal'] = int(mem.total / 1024 / 1024)
        val['MemFree'] = int(mem.free / 1024 / 1024)
        val['Buffers'] = int(mem.buffers / 1024 / 1024)
        val['Cached'] = int(mem.cached / 1024 / 1024)
        return val

    def update_graph(self):
        val = self._getvalues()
        self.push(
            val['MemTotal'] - val['MemFree'] - val['Buffers'] - val['Cached']
        )


class SwapGraph(_Graph):
    """Display a swap info graph.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """
    orientations = base.ORIENTATION_HORIZONTAL
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        val = self._getvalues()
        self.maxvalue = val['SwapTotal']
        swap = val['SwapTotal'] - val['SwapFree']
        self.fulfill(swap)

    def _getvalues(self):
        val = {}
        swap = psutil.swap_memory()
        val['SwapTotal'] = int(swap.total / 1024 / 1024)
        val['SwapFree'] = int(swap.free / 1024 / 1024)
        return val

    def update_graph(self):
        val = self._getvalues()

        swap = val['SwapTotal'] - val['SwapFree']

        # can change, swapon/off
        if self.maxvalue != val['SwapTotal']:
            self.maxvalue = val['SwapTotal']
            self.fulfill(swap)
        self.push(swap)


class NetGraph(_Graph):
    """Display a network usage graph.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            "interface",
            "auto",
            "Interface to display info for ('auto' for detection)"
        ),
        ("bandwidth_type", "down", "down(load)/up(load)"),
    ]

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(NetGraph.defaults)
        if self.interface == "auto":
            try:
                self.interface = self.get_main_iface()
            except RuntimeError:
                logger.warning(
                    "NetGraph - Automatic interface detection failed, "
                    "falling back to 'eth0'"
                )
                self.interface = "eth0"
        if self.bandwidth_type != "down" and self.bandwidth_type != "up":
            raise ValueError("bandwidth type {} not known!".format(self.bandwidth_type))
        self.bytes = 0
        self.bytes = self._get_values()

    def _get_values(self):
        net = psutil.net_io_counters(pernic=True)
        if self.bandwidth_type == "up":
            return net[self.interface].bytes_sent
        if self.bandwidth_type == "down":
            return net[self.interface].bytes_recv

    def update_graph(self):
        val = self._get_values()
        change = val - self.bytes
        self.bytes = val
        self.push(change)

    @staticmethod
    def get_main_iface():

        # XXX: psutil doesn't have the facility to get the main interface,
        # so I'll just return the interface that has received the most traffic.
        #
        # I could do this with netifaces, but that's another dependency.
        #
        # Oh. and there is probably a better way to do this.

        net = psutil.net_io_counters(pernic=True)
        iface = {}
        for entry in net:
            iface[entry] = net[entry].bytes_recv
        return sorted(iface.items(), key=operator.itemgetter(1))[-1][0]


class HDDGraph(_Graph):
    """Display HDD free or used space graph"""
    fixed_upper_bound = True
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("path", "/", "Partition mount point."),
        ("space_type", "used", "free/used")
    ]

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(HDDGraph.defaults)
        stats = statvfs(self.path)
        self.maxvalue = stats.f_blocks * stats.f_frsize
        values = self._get_values()
        self.fulfill(values)

    def _get_values(self):
        stats = statvfs(self.path)
        if self.space_type == 'used':
            return (stats.f_blocks - stats.f_bfree) * stats.f_frsize
        else:
            return stats.f_bavail * stats.f_frsize

    def update_graph(self):
        val = self._get_values()
        self.push(val)


class HDDBusyGraph(_Graph):
    """Display HDD busy time graph

    Parses /sys/block/<dev>/stat file and extracts overall device IO usage,
    based on ``io_ticks``'s value.  See
    https://www.kernel.org/doc/Documentation/block/stat.txt
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("device", "sda", "Block device to display info for")
    ]

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(HDDBusyGraph.defaults)
        self.path = '/sys/block/{dev}/stat'.format(
            dev=self.device
        )
        self._prev = 0

    def _get_values(self):
        try:
            # io_ticks is field number 9
            with open(self.path) as f:
                io_ticks = int(f.read().split()[9])
        except IOError:
            return 0
        activity = io_ticks - self._prev
        self._prev = io_ticks
        return activity

    def update_graph(self):
        val = self._get_values()
        self.push(val)
