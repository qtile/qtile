import time
import cairo

from . import base
from .. import manager, bar, hook, utils

__all__ = [
    'CPUGraph',
    'MemoryGraph',
    'SwapGraph',
]

class _Graph(base._Widget):
    fixed_upper_bound = False
    defaults = manager.Defaults(
        ("graph_color", "0000ff", "Graph color"),
        ("fill_color", "ff0000", "Fill color for linefill graph"),
        ("background", "000000", "Widget background"),
        ("border_color", "215578", "Widget border color"),
        ("border_width", 2, "Widget background"),
        ("margin_x", 3, "Margin X"),
        ("margin_y", 3, "Margin Y"),
        ("samples", 100, "Count of graph samples."),
        ("frequency", 0.5, "Update frequency in seconds"),
        ("type", "box", "'box', 'line', 'linefill'"),
        ("line_width", 5, "Line width"),
    )

    def __init__(self, width = 100, **config):
        base._Widget.__init__(self, width, **config)
        self.values = [0]*self.samples
        self.lasttick = 0
        self.maxvalue = 0

    @property
    def graphwidth(self):
        return self.width - self.border_width * 2 - self.margin_x * 2

    def draw_box(self, x, y, step, values):
        for val in values:
            self.drawer.fillrect(x, y-val, step, val, self.graph_color)
            x += step 

    def draw_line(self, x, y, step, values):
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.graph_color))
        self.drawer.ctx.set_line_width(self.line_width)
        self.drawer.ctx.move_to(x, y)
        for val in values:
            self.drawer.ctx.line_to(x, y-val)
            x += step 
        self.drawer.ctx.stroke()

    def draw_linefill(self, x, y, step, values):
        self.drawer.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.graph_color))
        self.drawer.ctx.set_line_width(self.line_width)
        self.drawer.ctx.move_to(x, y)
        current = x + step
        for val in values:
            self.drawer.ctx.line_to(current, y-val + self.line_width/2)
            current += step 
        self.drawer.ctx.stroke_preserve()
        self.drawer.ctx.line_to(current, y + self.line_width/2)
        self.drawer.ctx.line_to(x, y + self.line_width/2)
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.fill_color))
        self.drawer.ctx.fill()

    def draw(self):
        self.drawer.clear(self.background)
        if self.border_width:
            self.drawer.ctx.set_source_rgb(*utils.rgb(self.border_color))
            self.drawer.ctx.set_line_width(self.border_width)
            self.drawer.ctx.rectangle(
                self.margin_x, self.margin_y,
                self.graphwidth + self.border_width*2,
                self.bar.height - self.margin_y*2,
            )
            self.drawer.ctx.stroke()
        h = self.bar.height - self.margin_y*2 - self.border_width*2
        x = self.margin_x+self.border_width
        y = self.margin_y+self.border_width + h
        step = self.graphwidth/float(self.samples)
        k = 1.0/(self.maxvalue or 1)
        scaled = [h * val * k for val in reversed(self.values)]

        if self.type == "box":
            self.draw_box(x, y, step, scaled)
        elif self.type == "line":
            self.draw_line(x, y, step, scaled)
        elif self.type == "linefill":
            self.draw_linefill(x, y, step, scaled)
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
        hook.subscribe.tick(self.update)

    def update(self):
        t = time.time()
        if self.lasttick + self.frequency < t:
            self.lasttick = t
            self.update_graph()


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
        self.push(busy*100.0/(busy+nval[3]-oval[3]))
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
        for i in xrange(len(self.values)):
            self.values[i] = val['MemTotal'] - val['MemFree'] - val['Inactive']

    def _getvalues(self):
        return get_meminfo()

    def update_graph(self):
        val = self._getvalues()
        self.push(val['MemTotal'] - val['MemFree'] - val['Inactive'])


class SwapGraph(_Graph):
    def _getvalues(self):
        return get_meminfo()

    def update_graph(self):
        val = self._getvalues()
        self.push(val['SwapTotal'] - val['SwapFree'] - val['SwapCached'])
