import time
import cairo

from . import base
from .. import manager, hook

__all__ = [
    'CPUGraph',
    'MemoryGraph',
    'SwapGraph',
]

class _Graph(base._Widget):
    fixed_upper_bound = False
    defaults = manager.Defaults(
        ("graph_color", "18BAEB", "Graph color"),
        ("fill_color", "1667EB.3", "Fill color for linefill graph"),
        ("background", "000000", "Widget background"),
        ("border_color", "215578", "Widget border color"),
        ("border_width", 2, "Widget background"),
        ("margin_x", 3, "Margin X"),
        ("margin_y", 3, "Margin Y"),
        ("samples", 100, "Count of graph samples."),
        ("frequency", 1, "Update frequency in seconds"),
        ("type", "linefill", "'box', 'line', 'linefill'"),
        ("line_width", 3, "Line width"),
    )

    def __init__(self, width = 100, **config):
        base._Widget.__init__(self, width, **config)
        self.values = [0]*self.samples
        self.maxvalue = 0

    @property
    def graphwidth(self):
        return self.width - self.border_width*2 - self.margin_x*2

    @property
    def graphheight(self):
        return self.bar.height - self.margin_y*2 - self.border_width*2

    def draw_box(self, x, y, values):
        step = self.graphwidth/float(self.samples)
        for val in values:
            self.drawer.set_source_rgb(self.graph_color)
            self.drawer.fillrect(x, y-val, step, val)
            x += step 

    def draw_line(self, x, y, values):
        step = self.graphwidth/float(self.samples-1)
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.set_source_rgb(self.graph_color)
        self.drawer.ctx.set_line_width(self.line_width)
        for val in values:
            self.drawer.ctx.line_to(x, y-val)
            x += step 
        self.drawer.ctx.stroke()

    def draw_linefill(self, x, y, values):
        step = self.graphwidth/float(self.samples-1)
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.set_source_rgb(self.graph_color)
        self.drawer.ctx.set_line_width(self.line_width)
        current = x
        for val in values:
            self.drawer.ctx.line_to(current, y-val)
            current += step 
        self.drawer.ctx.stroke_preserve()
        self.drawer.ctx.line_to(current, y + self.line_width/2.0)
        self.drawer.ctx.line_to(x, y + self.line_width/2.0)
        self.drawer.set_source_rgb(self.fill_color)
        self.drawer.ctx.fill()

    def draw(self):
        self.drawer.clear(self.background)
        if self.border_width:
            self.drawer.set_source_rgb(self.border_color)
            self.drawer.ctx.set_line_width(self.border_width)
            self.drawer.ctx.rectangle(
                self.margin_x + self.border_width/2.0, self.margin_y + self.border_width/2.0,
                self.graphwidth + self.border_width,
                self.bar.height - self.margin_y*2 - self.border_width,
            )
            self.drawer.ctx.stroke()
        x = self.margin_x + self.border_width
        y = self.margin_y + self.graphheight + self.border_width
        k = 1.0/(self.maxvalue or 1)
        scaled = [self.graphheight * val * k for val in reversed(self.values)]

        if self.type == "box":
            self.draw_box(x, y, scaled)
        elif self.type == "line":
            self.draw_line(x, y, scaled)
        elif self.type == "linefill":
            self.draw_linefill(x, y, scaled)
        else:
            raise ValueError("Unknown graph type: %s."%self.type)

        self.drawer.draw(self.offset, self.width)

    def push(self, value):
        self.values.insert(0, value)
        self.values.pop()
        if not self.fixed_upper_bound:
            self.maxvalue = max(self.values)
        self.draw()

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.timeout_add(self.frequency, self.update)

    def update(self):
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
        busy = (nval[0]+nval[1]+nval[2] - oval[0]-oval[1]-oval[2])
        total = busy+nval[3]-oval[3]
        if total:
            # sometimes this value is zero for unknown reason (time shift?)
            # we just skip the value, because it gives us no info about
            # cpu load, if it's zero
            self.push(busy*100.0/total)
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

        mem = val['MemTotal'] - val['MemFree'] - val['Inactive']
        self.fullfill(mem)

    def _getvalues(self):
        return get_meminfo()

    def update_graph(self):
        val = self._getvalues()
        self.push(val['MemTotal'] - val['MemFree'] - val['Inactive'])


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
