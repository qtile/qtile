# -*- coding: utf-8 -*-
import sys

from .. import bar, manager
from libqtile.notify import manager as notifier
import base


class Notify(base._TextBox):
    """
        An notify widget
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Mpd widget font"),
        ("fontsize", None, "Mpd widget pixel size. Calculated if None."),
        ("padding", None, "Mpd widget padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        notifier.register(self.update)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(1, self.update)

    def update(self, notif):
        self.text = notif.summary
        if notif.body:
            self.text = '%s - %s' % (self.text, notif.body)
        if notif.timeout and notif.timeout > 0:
            self.timeout_add(notif.timeout / 1000, self.clear)
        self.bar.draw()
        return True

    def clear(self):
        self.text = ''
        self.bar.draw()

    def click(self, x, y, button):
        if button == 1:
            self.clear()
