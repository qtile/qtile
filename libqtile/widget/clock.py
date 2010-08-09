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
        self.current = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe("tick", self.update)
        self.text = datetime.datetime.now().strftime(self.FMT)
        self.guess_width()

    def update(self):
        now = datetime.datetime.now().strftime(self.FMT)
        if self.current != now:
            _, _, _, _, self.width, _  = self.drawer.text_extents(now)
            self.text = now
            self.guess_width()
            self.draw()


