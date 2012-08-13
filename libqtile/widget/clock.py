#!/usr/bin/env python
# coding: utf-8

from time import time
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
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, fmt="%c", width=bar.CALCULATED, **config):
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
        t = time()
        self.timeout_add((int(t) + 1.) - t, self._adjust)

    def _adjust(self):
        self.timeout_add(1, self.update)
        self.update()
        return False

    def update(self):
        now = datetime.datetime.now().strftime(self.fmt)
        if self.text != now:
            self.text = now
            self.bar.draw()
        return True

