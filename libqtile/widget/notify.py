# -*- coding: utf-8 -*-
import sys

from .. import bar, manager, drawer, utils
from libqtile.notify import notifier
import base


class Notify(base._TextBox):
    """
        An notify widget
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Mpd widget font"),
        ("fontsize", None, "Mpd widget pixel size. Calculated if None."),
        ("fontshadow", None,
            "font shadow color, default is None(no shadow)"),
        ("padding", None, "Mpd widget padding. Calculated if None."),
        ("background", None, "Background colour"),
        ("foreground", "ffffff", "Foreground normal priority colour"),
        ("foreground_urgent", "ff0000", "Foreground urgent priority colour"),
        ("foreground_low", "dddddd", "Foreground low priority  colour"),
    )

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        notifier.register(self.update)
        self.current_id = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font,
            self.fontsize, self.fontshadow, markup=True)

    def set_notif_text(self, notif):
        self.text = utils.escape(notif.summary)
        urgency = notif.hints.get('urgency', 1)
        if urgency != 1:
            self.text = '<span color="%s">%s</span>' % (
                utils.hex(self.foreground_urgent if urgency == 2
                          else self.foreground_low), self.text)
        if notif.body:
            self.text = '<span weight="bold">%s</span> - %s' % (
                self.text, utils.escape(notif.body))

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

    def button_press(self, x, y, button):
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
