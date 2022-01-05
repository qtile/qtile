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

import sys
import time
from datetime import datetime, timedelta, timezone

from libqtile.log_utils import logger
from libqtile.widget import base

try:
    import pytz
except ImportError:
    pass

try:
    import dateutil.tz
except ImportError:
    pass


class Clock(base.InLoopPollText):
    """A simple but flexible text-based clock"""

    defaults = [
        ("format", "%H:%M", "A Python datetime format string"),
        ("update_interval", 1.0, "Update interval for the clock"),
        (
            "timezone",
            None,
            "The timezone to use for this clock, either as"
            ' string if pytz or dateutil is installed (e.g. "US/Central" or'
            " anything in /usr/share/zoneinfo), or as tzinfo (e.g."
            " datetime.timezone.utc). None means the system local timezone and is"
            " the default.",
        ),
    ]
    DELTA = timedelta(seconds=0.5)

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Clock.defaults)
        if isinstance(self.timezone, str):
            if "pytz" in sys.modules:
                self.timezone = pytz.timezone(self.timezone)
            elif "dateutil" in sys.modules:
                self.timezone = dateutil.tz.gettz(self.timezone)
            else:
                logger.warning(
                    "Clock widget can not infer its timezone from a"
                    " string without pytz or dateutil. Install one"
                    " of these libraries, or give it a"
                    " datetime.tzinfo instance."
                )
        if self.timezone is None:
            logger.debug("Defaulting to the system local timezone.")

    def tick(self):
        self.update(self.poll())
        return self.update_interval - time.time() % self.update_interval

    # adding .5 to get a proper seconds value because glib could
    # theoreticaly call our method too early and we could get something
    # like (x-1).999 instead of x.000
    def poll(self):
        if self.timezone:
            now = datetime.now(timezone.utc).astimezone(self.timezone)
        else:
            now = datetime.now(timezone.utc).astimezone()
        return (now + self.DELTA).strftime(self.format)
