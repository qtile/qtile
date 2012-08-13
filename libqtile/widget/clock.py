#!/usr/bin/env python
# coding: utf-8

from time import time
from datetime import datetime

import gobject

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

    def update(self):
        new_text = datetime.now().strftime(self.fmt)
        if new_text != self.text:
            self.text = new_text
            self.bar.draw()
        t = int(time() * 1000)
        gobject.timeout_add(1000 - t % 1000, self.update,
                            priority=gobject.PRIORITY_HIGH)
        return False

