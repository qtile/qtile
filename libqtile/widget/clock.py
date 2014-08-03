from time import time
from datetime import datetime
from contextlib import contextmanager
from . import base

import os

@contextmanager
def tz(the_tz):
    orig = os.environ.get('TZ')
    os.environ['TZ'] = the_tz
    yield
    if orig is not None:
        os.environ['TZ'] = orig
    else:
        del os.environ['TZ']

class Clock(base.InLoopPollText):
    """
        A simple but flexible text-based clock.
    """
    defaults = [
        ('format', '%H:%M', 'A Python datetime format string'),
        ('update_interval', 1., 'Update interval for the clock'),
        ('timezone', None, 'The timezone to use for this clock, '
            'e.g. "US/Central" (or anything in /usr/share/zoneinfo). None means '
            'the default timezone.')
    ]
    def __init__(self, fmt=None, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Clock.defaults)
        if fmt is not None:
            base.deprecated('fmt kwarg or positional argument is deprecated. '
                            'Please use format.')
            self.format = fmt

    def tick(self):
        ts = time()
        self.timeout_add(self.update_interval - ts % self.update_interval,
                         self.tick)
        self.update(self.poll())
        return False

    def _get_time(self):
        ts = time()
        # adding .5 to get a proper seconds value because glib could
        # theoreticaly call our method too early and we could get something
        # like (x-1).999 instead of x.000
        return datetime.fromtimestamp(int(ts + .5)).strftime(self.format)

    def poll(self):
        # We use None as a sentinel here because C's strftime defaults to UTC
        # if TZ=''.
        if self.timezone is not None:
            with tz(self.timezone):
                return self._get_time()
        else:
            return self._get_time()
