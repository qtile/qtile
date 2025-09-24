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
