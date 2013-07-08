import cairo

from . import base
from os import statvfs

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
        self.values = [0]*self.samples
        self.maxvalue = 0
        self.timeout_add(self.frequency, self.update)

    @property
    def graphwidth(self):
        return self.width - self.border_width * 2 - self.margin_x * 2

    @property
    def graphheight(self):
        return self.bar.height - self.margin_y * 2 - self.border_width * 2

    def draw_box(self, x, y, values):
        step = self.graphwidth / float(self.samples)
        self.drawer.set_source_rgb(self.graph_color)
        for val in values:
            val = self.val(val)
            self.drawer.fillrect(x, y - val, step, val)
            x += step

    def draw_line(self, x, y, values):
        step = self.graphwidth / float(self.samples - 1)
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.set_source_rgb(self.graph_color)
        self.drawer.ctx.set_line_width(self.line_width)
        for val in values:
            self.drawer.ctx.line_to(x, y - self.val(val))
            x += step
        self.drawer.ctx.stroke()

    def draw_linefill(self, x, y, values):
        step = self.graphwidth / float(self.samples - 2)
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.set_source_rgb(self.graph_color)
        self.drawer.ctx.set_line_width(self.line_width)
        for index, val in enumerate(values):
            self.drawer.ctx.line_to(x + index * step, y - self.val(val))
        self.drawer.ctx.stroke_preserve()
        self.drawer.ctx.line_to(x + (len(values) - 1) * step,
                                y - 1 + self.line_width / 2.0)
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

        self.drawer.draw(self.offset, self.width)

    def push(self, value):
        self.values.insert(0, value)
        self.values.pop()
        if not self.fixed_upper_bound:
            self.maxvalue = max(self.values)
        self.draw()

    def update(self):
        if self.configured:
            self.update_graph()
        return True

    def fullfill(self, value):
        self.values = [value] * len(self.values)


class CPUGraph(_Graph):
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.maxvalue = 100
        self.oldvalues = self._getvalues()

    def _getvalues(self):
        with open('/proc/stat') as file:
            all_cpus = next(file)
            name, user, nice, sys, idle, iowait, tail = all_cpus.split(None, 6)
            return int(user), int(nice), int(sys), int(idle)

    def update_graph(self):
        nval = self._getvalues()
        oval = self.oldvalues
        busy = (nval[0] + nval[1] + nval[2] - oval[0] - oval[1] - oval[2])
        total = busy + nval[3] - oval[3]
        if total:
            # sometimes this value is zero for unknown reason (time shift?)
            # we just skip the value, because it gives us no info about
            # cpu load, if it's zero
            self.push(busy * 100.0 / total)
        self.oldvalues = nval


def get_meminfo():
    with open('/proc/meminfo') as file:
        val = {}
        for line in file:
            key, tail = line.split(':')
            uv = tail.split()
            val[key] = int(uv[0])
    return val


class MemoryGraph(_Graph):
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        val = self._getvalues()
        self.maxvalue = val['MemTotal']

        mem = val['MemTotal'] - val['MemFree'] - val['Buffers'] - val['Cached']
        self.fullfill(mem)

    def _getvalues(self):
        return get_meminfo()

    def update_graph(self):
        val = self._getvalues()
        self.push(val['MemTotal'] - val['MemFree'] - val['Buffers'] - val['Cached'])


class SwapGraph(_Graph):
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        val = self._getvalues()
        self.maxvalue = val['SwapTotal']
        swap = val['SwapTotal'] - val['SwapFree'] - val['SwapCached']
        self.fullfill(swap)

    def _getvalues(self):
        return get_meminfo()

    def update_graph(self):
        val = self._getvalues()

        swap = val['SwapTotal'] - val['SwapFree'] - val['SwapCached']

        # can change, swapon/off
        if self.maxvalue != val['SwapTotal']:
            self.maxvalue = val['SwapTotal']
            self.fullfill(swap)
        self.push(swap)


class NetGraph(_Graph):
    defaults = [
        ("interface", "auto",
         "Interface to display info for ('auto' for detection)"),
        ("bandwidth_type", "down", "down(load)/up(load)"),
    ]

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(NetGraph.defaults)
        if self.interface == "auto":
            try:
                self.interface = self.get_main_iface()
            except RuntimeError:
                self.log.warning("NetGraph - Automatic interface detection failed, falling back to 'eth0'")
                self.interface = "eth0"
        self.filename = '/sys/class/net/{interface}/statistics/{type}'.format(
            interface=self.interface,
            type=self.bandwidth_type == 'down' and 'rx_bytes' or 'tx_bytes'
        )
        self.bytes = 0
        self.bytes = self._getValues()

    def _getValues(self):
        try:
            with open(self.filename) as file:
                val = int(file.read())
                rval = val - self.bytes
                self.bytes = val
                return rval
        except IOError:
            return 0

    def update_graph(self):
        val = self._getValues()
        self.push(val)

    @staticmethod
    def get_main_iface():
        filename = "/proc/net/route"
        make_route = lambda line: dict(zip(['iface', 'dest'], line.split()))
        routes = [make_route(line) for line in list(open(filename))[1:]]
        try:
            return next((r for r in routes if not int(r['dest'], 16)), routes[0])['iface']
        except:
            raise RuntimeError('No valid interfaces available')


class HDDGraph(_Graph):
    fixed_upper_bound = True
    defaults = [
        ("path", "/", "Partition mount point."),
        ("space_type", "used", "free/used")
    ]

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        self.add_defaults(HDDGraph.defaults)
        stats = statvfs(self.path)
        self.maxvalue = stats.f_blocks * stats.f_frsize
        values = self._getValues()
        self.fullfill(values)

    def _getValues(self):
        stats = statvfs(self.path)
        if self.space_type == 'used':
            return (stats.f_blocks - stats.f_bfree) * stats.f_frsize
        else:
            return stats.f_bavail * stats.f_frsize

    def update_graph(self):
        val = self._getValues()
        self.push(val)


class HDDBusyGraph(_Graph):
    """
    Parses /sys/block/<dev>/stat file and extracts overall device
    IO usage, based on `io_ticks`'s value.
    See https://www.kernel.org/doc/Documentation/block/stat.txt
    """
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

    def _getActivity(self):
        try:
            # io_ticks is field number 9
            io_ticks = int(open(self.path).read().split()[9])
        except IOError:
            return 0
        activity = io_ticks - self._prev
        self._prev = io_ticks
        return activity

    def update_graph(self):
        self.push(self._getActivity())
