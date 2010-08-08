import sys
from .. import hook
import base

class WindowName(base._TextBox):
    defaults = dict(
        font = "Monospace",
        fontsize = None,
        padding_left = None,
        background = "000000",
        foreground = "ffffff"
    )
    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe("window_name_change", self.update)
        hook.subscribe("focus_change", self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        self.text = w.name if w else " "
        self.draw()


