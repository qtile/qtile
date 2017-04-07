# Copyright (c) 2017 Zordsdavini
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

import subprocess
from time import time
from datetime import datetime, timedelta
from . import base
from ..notify import notifier, Notification

import os

class Pomodoro(base.ThreadPoolText):
    """Pomodoro technique widget"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('fmt', '%s', 'fmt'),
        ('num_pomodori', 4, "Number of pomodori to do in a cycle"),
        ('length_pomodori', 25, "Length of one pomodori in minutes"),
        ('length_short_break', 5, "Length of a short break in minutes"),
        ('length_long_break', 15, "Length of a long break in minutes"),
        ('color_inactive', "ff0000", "Colour then pomodoro is inactive"),
        ('color_active', "00ff00", "Colour then pomodoro is running"),
        ('color_break', "ffff00", "Colour then it is break time"),
        ('notification_on', True, "Turn notifications on"),
        ('prefix',
            {
                'inactive': 'POMODORO',
                'active' : '',
                'break' : 'B ',
                'long_break': 'LB ',
                'paused': 'PAUSE'
                },
            "Prefix for status"),
        ("update_interval", 1, "Update interval in seconds, if none, the "
            "widget updates whenever the event loop is idle."),
    ]

    STATUS_START = "start"
    STATUS_INACTIVE = "inactive"
    STATUS_ACTIVE = "active"
    STATUS_BREAK = "break"
    STATUS_LONG_BREAK = "long_break"
    STATUS_PAUSED = "paused"

    status = "inactive"
    paused_status = None
    notified = False
    end_time = datetime.now()
    time_left = None
    pomodoros = 1

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Pomodoro.defaults)

    def tick(self):
        self.update(self.poll())
        return self.update_interval - time() % self.update_interval

    def _update(self):
        if self.status in [self.STATUS_INACTIVE, self.STATUS_PAUSED]:
            return

        if self.end_time > datetime.now() and self.status != self.STATUS_START:
            return

        if self.status == self.STATUS_ACTIVE and self.pomodoros == self.num_pomodori:
            self.status = self.STATUS_LONG_BREAK
            self.end_time = datetime.now() + timedelta(minutes=self.length_long_break)
            self.pomodoros = 1
            if self.notification_on:
                self._send_notification('normal', "Please take a long break! End Time: " + self.end_time.strftime("%H:%M"))
            return

        if self.status == self.STATUS_ACTIVE:
            self.status = self.STATUS_BREAK
            self.end_time = datetime.now() + timedelta(minutes=self.length_short_break)
            self.pomodoros += 1
            if self.notification_on:
                self._send_notification('normal', "Please take a short break! End Time: " + self.end_time.strftime("%H:%M"))
            return

        self.status = self.STATUS_ACTIVE
        self.end_time = datetime.now() + timedelta(minutes=self.length_pomodori)
        if self.notification_on:
            self._send_notification('critical', "Please start with the next Pomodori! End Time: " + self.end_time.strftime("%H:%M"))

        return


    def _get_text(self):
        self._update()

        if self.status in [self.STATUS_INACTIVE, self.STATUS_PAUSED]:
            self.layout.colour = self.color_inactive
            return self.prefix[self.status]

        time_left = self.end_time - datetime.now()

        if self.status == self.STATUS_ACTIVE:
            self.layout.colour = self.color_active
        else:
            self.layout.colour = self.color_break

        return self.prefix[self.status] + "%i:%i:%s" % (time_left.seconds // 3600, time_left.seconds % 3600 // 60, time_left.seconds % 60)

    def _toggle_break(self):
        if self.status == self.STATUS_INACTIVE:
            self.status = self.STATUS_START
            return

        if self.paused_status == None:
            self.paused_status = self.status
            self.time_left = self.end_time - datetime.now()
            self.status = self.STATUS_PAUSED
            if self.notification_on:
                self._send_notification('low', "Pomodoro has been paused")
        else:
            self.status = self.paused_status
            self.paused_status = None
            self.end_time = self.time_left + datetime.now()
            if self.notification_on:
                if self.status == self.STATUS_ACTIVE:
                    status = 'Pomodoro'
                else:
                    status = 'break'

                self._send_notification('normal', "Please continue on %s! End Time: " % status + self.end_time.strftime("%H:%M"))

    def _toggle_active(self):
        if self.status != self.STATUS_INACTIVE:
            self.status = self.STATUS_INACTIVE
            if self.notification_on:
                self._send_notification('critical', "Pmodoro has been suspended")
        else:
            self.status = self.STATUS_START

    def _send_notification(self, urgent, message):
        subprocess.Popen(['notify-send', "Pomodoro", message, '-u', urgent, '-t', '5000'])

    def poll(self):
        return self.fmt % self._get_text()

    def button_press(self, x, y, button):
        """What to do when press a mouse button over the Pomodoro widget.
        LEFT BUTTON: pause/resume current status or start
        RIGHT BUTTON: toggle activity

        """
        print(button)
        if button == 1:
            self._toggle_break()
        elif button == 3:
            self._toggle_active()

        base.ThreadedPollText.button_press(self, x, y, button)
