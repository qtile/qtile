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

from typing import Any

from libqtile import bar, hook
from libqtile.command.base import expose_command
from libqtile.layout import plasma
from libqtile.layout.plasma import AddMode
from libqtile.widget import base


class Plasma(base._TextBox):
    """
    A simple widget to indicate in which direction new windows will be
    added in the Plasma layout.
    """

    defaults: list[tuple[str, Any, str]] = [
        ("horizontal", "H", "Text to display if horizontal mode"),
        ("vertical", "V", "Text to display if horizontal mode"),
        ("split", "S", "Text to append to mode if ``horizontal/vertical_split`` not set"),
        ("horizontal_split", None, "Text to display for horizontal split mode"),
        ("vertical_split", None, "Text to display for horizontal split mode"),
        ("format", "{mode:>2}", "Format appearance of text"),
    ]

    def __init__(self, text="", width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, text=text, width=width, **config)
        self.add_defaults(Plasma.defaults)
        self.add_callbacks({"Button1": self.next_mode})

        if self.horizontal_split is None:
            self.horizontal_split = self.horizontal + self.split

        if self.vertical_split is None:
            self.vertical_split = self.vertical + self.split

        self.modes = [
            AddMode.HORIZONTAL,
            AddMode.HORIZONTAL | AddMode.SPLIT,
            AddMode.VERTICAL,
            AddMode.VERTICAL | AddMode.SPLIT,
        ]
        self._mode = self.modes[0]
        self._layout = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.plasma_add_mode(self.mode_changed)
        hook.subscribe.layout_change(self.layout_changed)
        self.mode_changed(bar.screen.group.layout)

    def mode_changed(self, layout):
        """Update text depending on add_mode of layout."""
        if not isinstance(layout, plasma.Plasma):
            self.update("")
            self._layout = None
            return

        self._layout = layout

        if layout.group and layout.group.screen is not self.bar.screen:
            return

        if layout.horizontal:
            if layout.split:
                mode = self.horizontal_split
                self._mode = AddMode.HORIZONTAL | AddMode.SPLIT
            else:
                mode = self.horizontal
                self._mode = AddMode.HORIZONTAL
        else:
            if layout.split:
                mode = self.vertical_split
                self._mode = AddMode.VERTICAL | AddMode.SPLIT
            else:
                mode = self.vertical
                self._mode = AddMode.VERTICAL

        self.update(self.format.format(mode=mode))

    def layout_changed(self, layout, group):
        """Update widget when layout changes."""
        if group.screen is self.bar.screen:
            self.mode_changed(layout)

    def finalize(self):
        hook.unsubscribe.plasma_add_mode(self.mode_changed)
        hook.unsubscribe.layout_change(self.layout_changed)
        base._TextBox.finalize(self)

    @expose_command()
    def next_mode(self):
        """Change the add mode for the Plasma layout."""
        if self._layout is None:
            return

        index = self.modes.index(self._mode)
        index = (index + 1) % len(self.modes)

        self._layout.add_mode = self.modes[index]
