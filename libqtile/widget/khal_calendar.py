# -*- coding: utf-8 -*-
###################################################################
# This widget will display the next appointment on your calendar in
# the qtile status bar. Appointments within the "reminder" time will be
# highlighted. Authentication credentials are stored on disk.
#
# This widget uses the khal command line calendar utility available at
# https://github.com/geier/khal
#
# This widget also requires the dateutil.parser module.
# If you get a strange "AttributeError: 'module' object has no attribute
# GoogleCalendar" error, you are probably missing a module. Check
# carefully.
#
# Thanks to the creator of the YahooWeather widget (dmpayton). This code
# borrows liberally from that one.
#
# Copyright (c) 2016 by David R. Andersen <k0rx@RXcomm.net>
# New khal output format adjustment, 2016 Christoph Lassner
# Licensed under the Gnu Public License
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
###################################################################

import datetime
import string
import subprocess

import dateutil.parser

from libqtile import utils
from libqtile.widget import base


class KhalCalendar(base.ThreadedPollText):
    """Khal calendar widget

    This widget will display the next appointment on your Khal calendar in the
    qtile status bar. Appointments within the "reminder" time will be
    highlighted.

    Widget requirements: dateutil_.

    .. _dateutil: https://pypi.org/project/python-dateutil/
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            'reminder_color',
            'FF0000',
            'color of calendar entries during reminder time'
        ),
        ('foreground', 'FFFF33', 'default foreground color'),
        ('remindertime', 10, 'reminder time in minutes'),
        ('lookahead', 7, 'days to look ahead in the calendar'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(KhalCalendar.defaults)
        self.text = 'Calendar not initialized.'
        self.default_foreground = self.foreground

    def poll(self):
        # get today and tomorrow
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        # get reminder time in datetime format
        remtime = datetime.timedelta(minutes=self.remindertime)

        # parse khal output for the next seven days
        # and get the next event
        args = ['khal', 'agenda', '--days', str(self.lookahead)]
        cal = subprocess.Popen(args, stdout=subprocess.PIPE)
        output = cal.communicate()[0].decode('utf-8')
        output = output.split('\n')
        if len(output) < 2:
            return 'No appointments scheduled'
        date = 'unknown'
        endtime = None
        for i in range(len(output)):  # pylint: disable=consider-using-enumerate
            if output[i].strip() == '':
                continue
            try:
                starttime = dateutil.parser.parse(date + ' ' + output[i][:5],
                                                  ignoretz=True)
                endtime = dateutil.parser.parse(date + ' ' + output[i][6:11],
                                                ignoretz=True)
            except ValueError:
                try:
                    if output[i] == 'Today:':
                        date = str(now.month) + '/' + str(now.day) + '/' + \
                            str(now.year)
                    elif output[i] == 'Tomorrow:':
                        date = str(tomorrow.month) + '/' + str(tomorrow.day) + \
                            '/' + str(tomorrow.year)
                    else:
                        dateutil.parser.parse(output[i])
                        date = output[i]
                        continue
                except ValueError:
                    pass  # no date.
            if endtime is not None and endtime > now:
                data = date.replace(':', '') + ' ' + output[i]
                break
            else:
                data = 'No appointments in next ' + \
                    str(self.lookahead) + ' days'

        # get rid of any garbage in appointment added by khal
        data = ''.join(filter(lambda x: x in string.printable, data))
        # colorize the event if it is within reminder time
        if (starttime - remtime <= now) and (endtime > now):
            self.foreground = utils.hex(self.reminder_color)
        else:
            self.foreground = self.default_foreground

        return data
