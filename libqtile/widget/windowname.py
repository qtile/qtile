import sys
from .. import hook, bar
import base

class WindowName(base._TextBox):
    """
        Displays the name of the window that currently has focus.
    """
    defaults = dict(
        font = "Monospace",
        fontsize = None,
        padding = None,
        background = "000000",
        foreground = "ffffff"
    )
    def __init__(self, **attrs):
        base._TextBox.__init__(self, width=bar.STRETCH, **attrs)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe("window_name_change", self.update)
        hook.subscribe("focus_change", self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        self.text = w.name if w else " "
        self.draw()


