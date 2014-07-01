# -*- coding: utf-8 -*-
import sys

from . import base
from .. import bar, utils
from libqtile.notify import notifier


class Notify(base._TextBox):
    """
        An notify widget
    """
    defaults = [
        ("foreground_urgent", "ff0000", "Foreground urgent priority colour"),
        ("foreground_low", "dddddd", "Foreground low priority  colour"),
        (
            "default_timeout",
            None,
            "Default timeout (seconds) for notifications"
        ),
    ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(Notify.defaults)
        notifier.register(self.update)
        self.current_id = 0

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=True
        )

    def set_notif_text(self, notif):
        self.text = utils.escape(notif.summary)
        urgency = notif.hints.get('urgency', 1)
        if urgency != 1:
            self.text = '<span color="%s">%s</span>' % (
                utils.hex(
                    self.foreground_urgent if urgency == 2
                    else self.foreground_low
                ),
                self.text
            )
        if notif.body:
            self.text = '<span weight="bold">%s</span> - %s' % (
                self.text, utils.escape(notif.body)
            )

    def update(self, notif):
        self.set_notif_text(notif)
        self.current_id = notif.id - 1
        if notif.timeout and notif.timeout > 0:
            self.timeout_add(notif.timeout / 1000, self.clear)
        elif self.default_timeout:
            self.timeout_add(self.default_timeout, self.clear)
        self.bar.draw()
        return True

    def display(self):
        self.set_notif_text(notifier.notifications[self.current_id])
        self.bar.draw()

    def clear(self):
        self.text = ''
        self.current_id = len(notifier.notifications) - 1
        self.bar.draw()

    def prev(self):
        if self.current_id > 0:
            self.current_id -= 1
        self.display()

    def next(self):
        if self.current_id < len(notifier.notifications) - 1:
            self.current_id += 1
            self.display()

    def button_press(self, x, y, button):
        if button == 1:
            self.clear()
        elif button == 4:
            self.prev()
        elif button == 5:
            self.next()

    def cmd_display(self):
        self.display()

    def cmd_clear(self):
        self.clear()

    def cmd_toggle(self):
        if self.text == '':
            self.display()
        else:
            self.clear()

    def cmd_prev(self):
        self.prev()

    def cmd_next(self):
        self.next()
