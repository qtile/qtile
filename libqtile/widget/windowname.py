import sys
from .. import hook, bar, manager
import base

class WindowName(base._TextBox):
    """
        Displays the name of the window that currently has focus.
    """
    defaults = manager.Defaults(
        ("font", "Monospace", "Font face."),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("padding", None, "Padding left and right."),
        ("background", "000000", "Background colour."),
        ("foreground", "ffffff", "Foreground colour."),
    )
    def __init__(self, **config):
        base._TextBox.__init__(self, width=bar.STRETCH, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe("window_name_change", self.update)
        hook.subscribe("focus_change", self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        self.text = w.name if w else " "
        self.draw()


