# Copyright (c) 2022 elParaguayo
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

import libqtile.layout
from libqtile import hook
from libqtile.lazy import lazy
from libqtile.widget import TextBox


class ScreenSplit(TextBox):
    """
    A simple widget to show the name of the current split and layout for the
    ``ScreenSplit`` layout.
    """

    defaults = [("format", "{split_name} ({layout})", "Format string.")]

    def __init__(self, **config):
        TextBox.__init__(self, "", **config)
        self.add_defaults(ScreenSplit.defaults)
        self.add_callbacks(
            {
                "Button4": lazy.layout.previous_split().when(layout="screensplit"),
                "Button5": lazy.layout.next_split().when(layout="screensplit"),
            }
        )
        self._drawn = False

    def _configure(self, qtile, bar):
        TextBox._configure(self, qtile, bar)
        self._set_hooks()

    def _set_hooks(self):
        hook.subscribe.layout_change(self._update)

    def _update(self, layout, group):
        if not self.configured:
            return

        if isinstance(layout, libqtile.layout.ScreenSplit) and group is self.bar.screen.group:
            split_name = layout.active_split.name
            layout_name = layout.active_layout.name
            self.set_text(split_name, layout_name)
        else:
            self.clear()

    def set_text(self, split_name, layout):
        self.update(self.format.format(split_name=split_name, layout=layout))

    def clear(self):
        self.update("")

    def finalize(self):
        hook.unsubscribe.layout_change(self._update)
        TextBox.finalize(self)

    def draw(self):
        # Force the widget to check layout the first time it's drawn
        if not self._drawn:
            self._update(self.bar.screen.group.layout, self.bar.screen.group)
            self._drawn = True
            return

        TextBox.draw(self)
