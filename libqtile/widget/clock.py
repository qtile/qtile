import datetime
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
        self.timeout_add(1, self.update)

    def update(self):
        if self.configured:
            now = datetime.datetime.now().strftime(self.fmt)
            if self.text != now:
                self.text = now
                self.bar.draw()
        return True
