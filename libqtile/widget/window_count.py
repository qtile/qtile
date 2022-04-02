# Copyright (c) 2020 elParaguayo
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

from typing import Any

from libqtile import bar, hook
from libqtile.widget import base


class WindowCount(base._TextBox):
    """
    A simple widget to display the number of windows in the
    current group of the screen on which the widget is.
    """

    defaults = [
        ("font", "sans", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None, "font shadow color, default is None(no shadow)"),
        ("padding", None, "Padding left and right. Calculated if None."),
        ("foreground", "#ffffff", "Foreground colour."),
        ("text_format", "{num}", "Format for message"),
        ("show_zero", False, "Show window count when no windows"),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, width=width, **config)
        self.add_defaults(WindowCount.defaults)
        self._count = 0

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self._setup_hooks()
        self._wincount()

    def _setup_hooks(self):
        hook.subscribe.client_killed(self._win_killed)
        hook.subscribe.client_managed(self._wincount)
        hook.subscribe.current_screen_change(self._wincount)
        hook.subscribe.setgroup(self._wincount)

    def _wincount(self, *args):
        try:
            self._count = len(self.bar.screen.group.windows)
        except AttributeError:
            self._count = 0

        self.update(self.text_format.format(num=self._count))

    def _win_killed(self, window):
        try:
            self._count = len(self.bar.screen.group.windows)
            if window.group == self.bar.screen.group:
                self._count -= 1
        except AttributeError:
            self._count = 0

        self.update(self.text_format.format(num=self._count))

    def calculate_length(self):
        if self.text and (self._count or self.show_zero):
            return min(self.layout.width, self.bar.width) + self.actual_padding * 2
        else:
            return 0

    def cmd_get(self):
        """Retrieve the current text."""
        return self.text
