# -*- coding: utf-8 -*-
import sys

from .. import bar, manager, drawer
from libqtile.notify import notifier
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
        self.current_id = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font, self.fontsize,
            markup=True)

    def set_notif_text(self, notif):
        self.text = notif.summary
        if notif.body:
            self.text = '<span weight="bold">%s</span> - %s' % (
                self.text, notif.body)

    def update(self, notif):
        self.set_notif_text(notif)
        self.current_id = notif.id - 1
        if notif.timeout and notif.timeout > 0:
            self.timeout_add(notif.timeout / 1000, self.clear)
        self.bar.draw()
        return True

    def diplay(self):
        self.set_notif_text(notifier.notifications[self.current_id])
        self.bar.draw()

    def clear(self):
        self.text = ''
        self.current_id = len(notifier.notifications) - 1
        self.bar.draw()

    def click(self, x, y, button):
        if button == 1:
            self.clear()
        elif button == 4:
            if self.current_id > 0:
                self.current_id -= 1
                self.diplay()
        elif button == 5:
            if self.current_id < len(notifier.notifications) - 1:
                self.current_id += 1
                self.diplay()
