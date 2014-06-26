from time import time
from datetime import datetime
from . import base

import warnings

class Clock(base.InLoopPollText):
    """
        A simple but flexible text-based clock.
    """
    defaults = [
        ('format', '%H:%M', 'A Python datetime format string'),

        ('update_interval', 1., 'Update interval for the clock'),
    ]
    def __init__(self, fmt=None, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Clock.defaults)
        if fmt is not None:
            warnings.warn('fmt kwarg or positional argument is deprecated. '
                          'Please use format.', DeprecationWarning)
            self.format = fmt

    def tick(self):
        ts = time()
        self.timeout_add(self.update_interval - ts % self.update_interval,
                         self.tick)
        self.update(self.poll())
        return False

    def poll(self):
        ts = time()
        # adding .5 to get a proper seconds value because glib could
        # theoreticaly call our method too early and we could get something
        # like (x-1).999 instead of x.000
        return datetime.fromtimestamp(int(ts + .5)).strftime(self.format)
