# -*- coding: utf-8 -*-
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 roger
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from . import base
from .. import bar, utils, pangocffi
from libqtile.notify import notifier
from os import path

class Notify(base._TextBox):
    """A notify widget"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("foreground_urgent", "ff0000", "Foreground urgent priority colour"),
        ("foreground_low", "dddddd", "Foreground low priority  colour"),
        (
            "default_timeout",
            None,
            "Default timeout (seconds) for notifications"
        ),
        ("audiofile", None, "Audiofile played during notifications"),
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
        self.text = pangocffi.markup_escape_text(notif.summary)
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
                self.text, pangocffi.markup_escape_text(notif.body)
            )
        if self.audiofile and path.exists(self.audiofile):
            self.qtile.cmd_spawn("aplay -q '%s'" % self.audiofile)

    def update(self, notif):
        self.qtile.call_soon_threadsafe(self.real_update, notif)

    def real_update(self, notif):
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
        """Display the notifcication"""
        self.display()

    def cmd_clear(self):
        """Clear the notification"""
        self.clear()

    def cmd_toggle(self):
        """Toggle showing/clearing the notification"""
        if self.text == '':
            self.display()
        else:
            self.clear()

    def cmd_prev(self):
        """Show previous notification"""
        self.prev()

    def cmd_next(self):
        """Show next notification"""
        self.next()
