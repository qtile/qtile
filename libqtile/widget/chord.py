# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Tycho Andersen
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

from libqtile import bar, hook
from libqtile.widget import base


class Chord(base._TextBox):
    """Display current key chord"""

    defaults = [
        (
            "chords_colors",
            {},
            "colors per chord in form of tuple {'chord_name': ('bg', 'fg')}. "
            "Where a chord name is not in the dictionary, the default ``background`` and ``foreground``"
            " values will be used.",
        ),
        (
            "name_transform",
            lambda txt: txt,
            "preprocessor for chord name it is pure function string -> string",
        ),
    ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(Chord.defaults)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.default_background = self.background
        self.default_foreground = self.foreground
        self.text = ""
        self._setup_hooks()

    def _setup_hooks(self):
        def hook_enter_chord(chord_name):
            if chord_name is True:
                self.text = ""
                self.reset_colours()
                return

            self.text = self.name_transform(chord_name)
            if chord_name in self.chords_colors:
                self.background, self.layout.colour = self.chords_colors.get(chord_name)
            else:
                self.reset_colours()

            self.bar.draw()

        hook.subscribe.enter_chord(hook_enter_chord)
        hook.subscribe.leave_chord(self.clear)

    def reset_colours(self):
        self.background = self.default_background
        self.layout.colour = self.default_foreground

    def clear(self, *args):
        self.reset_colours()
        self.text = ""
        self.bar.draw()
