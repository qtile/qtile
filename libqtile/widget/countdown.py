# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Tycho Andersen
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

from datetime import datetime

from . import base


class Countdown(base.InLoopPollText):
    """
        A simple countdown timer text widget.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('format', '{D}d {H}h {M}m {S}s',
            'Format of the displayed text. Available variables:'
            '{D} == days, {H} == hours, {M} == minutes, {S} seconds.'),
        ('update_interval', 1., 'Update interval in seconds for the clock'),
        ('date', datetime.now(), "The datetime for the endo of the countdown"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Countdown.defaults)

    def poll(self):
        now = datetime.now()

        days = hours = minutes = seconds = 0
        if not self.date < now:
            delta = self.date - now
            days = delta.days
            hours, rem = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(rem, 60)

        data = {"D": "%02d" % days,
                "H": "%02d" % hours,
                "M": "%02d" % minutes,
                "S": "%02d" % seconds}

        return self.format.format(**data)
