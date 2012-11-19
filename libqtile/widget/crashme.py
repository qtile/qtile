# -*- coding: utf-8 -*-
from .. import bar, manager
import base


class _CrashMe(base._TextBox):
    """
        A developper widget to force a crash in qtile
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", None, "Background colour"),
        ("foreground", "ff0000", "Foreground colour")
    )

    def __init__(self, width=bar.CALCULATED, **config):
        """
            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        base._TextBox.__init__(self, "Crash me !", width, **config)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font, self.fontsize,
            markup=True)

    def button_press(self, x, y, button):
        if button == 1:
            1 / 0
        elif button == 3:
            self.text = '<span>\xC3GError'
            self.bar.draw()
