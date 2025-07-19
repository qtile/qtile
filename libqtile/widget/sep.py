# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012, 2015 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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

from libqtile.widget import base


class Sep(base._Widget):
    """A visible widget separator"""

    orientations = base.ORIENTATION_BOTH
    defaults = [
        ("padding", 2, "Padding on either side of separator."),
        ("linewidth", 1, "Width of separator line."),
        ("foreground", "888888", "Separator line colour."),
        ("size_percent", 80, "Size as a percentage of bar size (0-100)."),
    ]

    def __init__(self, **config):
        length = config.get("padding", 2) * 2 + config.get("linewidth", 1)
        base._Widget.__init__(self, length, **config)
        self.add_defaults(Sep.defaults)
        self.length = self.padding + self.linewidth

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        margin = (self.bar.size / float(100) * (100 - self.size_percent)) / 2.0
        if self.bar.horizontal:
            self.drawer.draw_vbar(
                self.foreground,
                float(self.length) / 2,
                margin,
                self.bar.size - margin,
                linewidth=self.linewidth,
            )
        else:
            self.drawer.draw_hbar(
                self.foreground,
                margin,
                self.bar.size - margin,
                float(self.length) / 2,
                linewidth=self.linewidth,
            )
        self.draw_at_default_position()
