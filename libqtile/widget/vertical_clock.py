# Copyright (c) 2024 elParaguayo
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
from datetime import datetime, timezone

from libqtile.confreader import ConfigError
from libqtile.widget import base
from libqtile.widget.clock import Clock


class VerticalClock(Clock):
    """
    A simple but flexible text-based clock for vertical bars.

    Unlike the ``Clock`` widget, ``VerticalClock`` will display text horizontally in the bar.
    """

    orientations = base.ORIENTATION_VERTICAL

    defaults = [
        (
            "format",
            ["%H", "%M"],
            "A list of Python datetime format string. Each string is printed as a separate line.",
        ),
        (
            "foreground",
            "fff",
            "Text colour. A single string will be applied to all fields. "
            "Alternatively, users can provide a list of strings with each colour being applied to the corresponding text format.",
        ),
        (
            "fontsize",
            None,
            "Font size. A single value will be applied to all fields. "
            "Alternatively, users can provide a list of sizes with each size being applied to the corresponding text format.",
        ),
    ]

    def __init__(self, **config):
        Clock.__init__(self, **config)
        self.add_defaults(VerticalClock.defaults)
        self.layouts = []

    def _to_list(self, value):
        return [value] * len(self.format)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if self.fontsize is None:
            self.fontsize = self._to_list(self.bar.size - self.bar.size / 5)
        elif isinstance(self.fontsize, int):
            self.fontsize = self._to_list(self.fontsize)
        elif not isinstance(self.fontsize, list):
            raise ConfigError("'fontsize' should be an integer or a list of integers.")
        elif not all(isinstance(fontsize, int) for fontsize in self.fontsize):
            raise ConfigError("'fontsize' should be of integers.")
        elif len(self.fontsize) != len(self.format):
            raise ConfigError("'fontsize' list should have same number of items as 'format'.")

        if isinstance(self.foreground, str):
            self.foreground = self._to_list(self.foreground)
        elif not isinstance(self.foreground, list):
            raise ConfigError("'foreground' should be a string or a list of strings.")
        elif not all(isinstance(foreground, str) for foreground in self.foreground):
            raise ConfigError("'foreground' list should be of strings.")
        elif len(self.foreground) != len(self.format):
            raise ConfigError("'foreground' list should have same number of items as 'format'.")

        if self.padding is None:
            self.padding = (sum(self.fontsize) / len(self.fontsize)) // 2

        self.layouts = [
            self.drawer.textlayout(
                self.formatted_text,
                fg,
                self.font,
                size,
                self.fontshadow,
                markup=self.markup,
            )
            for _, fg, size in zip(self.format, self.foreground, self.fontsize)
        ]

    def calculate_length(self):
        return sum(l.height + self.padding for l in self.layouts) + self.padding

    def update(self, time):
        for layout, fmt in zip(self.layouts, self.format):
            layout.text = time.strftime(fmt)
            layout.width = self.bar.size
        self.draw()

    @property
    def can_draw(self):
        return all(layout is not None for layout in self.layouts)

    # adding .5 to get a proper seconds value because glib could
    # theoreticaly call our method too early and we could get something
    # like (x-1).999 instead of x.000
    def poll(self):
        if self.timezone:
            now = datetime.now(timezone.utc).astimezone(self.timezone)
        else:
            now = datetime.now(timezone.utc).astimezone()
        return now + self.DELTA

    def draw(self):
        if not self.can_draw:
            return
        offset = self.padding
        self.drawer.clear(self.background or self.bar.background)

        for layout in self.layouts:
            self.drawer.ctx.save()
            self.drawer.ctx.translate(0, offset)
            layout.draw(0, 0)
            offset += layout.height + self.padding
            self.drawer.ctx.restore()

        self.draw_at_default_position()

    def finalize(self):
        for layout in self.layouts:
            layout.finalize()
            layout = None

        base._Widget.finalize(self)
