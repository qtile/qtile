import collections

from . import base
from .. import manager, bar, hook, utils

__all__ = [
    'CPUGraph',
    'MemoryGraph',
    'SwapGraph',
    ]

class _Graph(base._Widget):
    ticks = 0
    fixed_upper_bound = False
    defaults = manager.Defaults(
        ("foreground", "0000ff", "Bars color"),
        ("background", "000000", "Widget background"),
        ("border_color", "215578", "Widget border color"),
        ("border_width", 2, "Widget background"),
        ("margin_x", 3, "Margin X"),
        ("margin_y", 3, "Margin Y"),
        ("bars", 32, "Count of graph bars"),
        ("bar_width", 1, "Width of single bar"),
        ("frequency", 100, "Amount of ticks for update"),
        )

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.values = collections.deque([0]*self.bars)
        self.maxvalue = 0

    def calculate_width(self):
        return self.bars*self.bar_width + self.border_width*2 + self.margin_x*2

    def draw(self):
        self.drawer.clear(self.background)
        if self.border_width:
            self.drawer.ctx.set_source_rgb(*utils.rgb(self.border_color))
            self.drawer.rounded_rectangle(self.margin_x, self.margin_y,
                self.bars*self.bar_width + self.border_width*2,
                self.bar.height - self.margin_y*2,
                self.border_width)
        x = self.margin_x+self.border_width
        y = self.margin_y+self.border_width
        w = self.bar_width
        h = self.bar.height - self.margin_y*2 - self.border_width*2
        k = 1.0/(self.maxvalue or 1)
        for val in self.values:
            ch = int(round(h*val*k))
            self.drawer.fillrect(x, y+h-ch, w, ch, self.foreground)
            x += w
        self.drawer.draw()

    def push(self, value):
        self.values.append(value)
        self.values.popleft()
        if not self.fixed_upper_bound:
            self.maxvalue = max(self.values)
        self.draw()

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        hook.subscribe.tick(self.update)

    def update(self):
        self.ticks += 1
        if not (self.ticks % self.frequency):
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

class MemoryGraph(_Graph):
    fixed_upper_bound = True

    def __init__(self, **config):
        _Graph.__init__(self, **config)
        val = self._getvalues()
        self.maxvalue = val['MemTotal']
        for i in xrange(len(self.values)):
            self.values[i] = val['MemTotal'] - val['MemFree'] - val['Inactive']

    def _getvalues(self):
        with open('/proc/meminfo') as file:
            val = {}
            for line in file:
                key, tail = line.split(':')
                value, unit = tail.split()
                val[key] = int(value)
        return val

    def update_graph(self):
        val = self._getvalues()
        self.push(val['MemTotal'] - val['MemFree'] - val['Inactive'])

class SwapGraph(_Graph):

    def _getvalues(self):
        with open('/proc/meminfo') as file:
            val = {}
            for line in file:
                key, tail = line.split(':')
                value, unit = tail.split()
                val[key] = int(value)
        return val

    def update_graph(self):
        val = self._getvalues()
        self.push(val['SwapTotal'] - val['SwapFree'] - val['SwapCached'])
