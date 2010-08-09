import datetime
from .. import hook
import base

class Clock(base._TextBox):
    defaults = dict(
        font = "Monospace",
        fontsize = None,
        padding = None,
        background = "000000",
        foreground = "ffffff"
    )
    FMT = "%H:%M"
    def __init__(self, *args, **kwargs):
        base._TextBox.__init__(self, *args, **kwargs)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe("tick", self.update)

    def update(self):
        now = datetime.datetime.now().strftime(self.FMT)
        if self.text != now:
            _, _, _, _, self.width, _  = self.drawer.text_extents(now)
            self.text = now
            self.guess_width()
            self.draw()


