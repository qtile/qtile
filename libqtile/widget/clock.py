from time import time
from datetime import datetime

from .. import bar, manager
import base


class Clock(base._TextBox):
    """
        A simple but flexible text-based clock.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("fontshadow", None,
            "font shadow color, default is None(no shadow)"),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", None, "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, fmt="%H:%M", width=bar.CALCULATED, **config):
        """
            - fmt: A Python datetime format string.

            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.fmt = fmt
        base._TextBox.__init__(self, " ", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.update()

    def update(self):

        ts = time()

        self.timeout_add(1. - ts % 1., self.update)

        old_layout_width = self.layout.width

        # adding .5 to get a proper seconds value because glib could
        # theoreticaly call our method too early and we could get something
        # like (x-1).999 instead of x.000
        self.text = datetime.fromtimestamp(int(ts + .5)).strftime(self.fmt)

        if self.layout.width != old_layout_width:
            self.bar.draw()
        else:
            self.draw()

        return False
