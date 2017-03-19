# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2012 Andrew Grigorev
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
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

import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from . import base

import os

@contextmanager
def tz(the_tz):
    orig = os.environ.get('TZ')
    os.environ['TZ'] = the_tz
    time.tzset()
    yield
    if orig is not None:
        os.environ['TZ'] = orig
    else:
        del os.environ['TZ']
    time.tzset()

class Clock(base.InLoopPollText):
    """A simple but flexible text-based clock"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('format', '%H:%M', 'A Python datetime format string'),
        ('update_interval', 1., 'Update interval for the clock'),
        ('timezone', None, 'The timezone to use for this clock, '
            'e.g. "US/Central" (or anything in /usr/share/zoneinfo). None means '
            'the default timezone.')
    ]
    DELTA = timedelta(seconds=0.5)

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Clock.defaults)

    def tick(self):
        self.update(self.poll())
        return self.update_interval - time.time() % self.update_interval

    # adding .5 to get a proper seconds value because glib could
    # theoreticaly call our method too early and we could get something
    # like (x-1).999 instead of x.000
    def _get_time(self):
        return (datetime.now() + self.DELTA).strftime(self.format)

    def poll(self):
        # We use None as a sentinel here because C's strftime defaults to UTC
        # if TZ=''.
        if self.timezone is not None:
            with tz(self.timezone):
                return self._get_time()
        else:
            return self._get_time()
