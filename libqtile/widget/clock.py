from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone, tzinfo

from libqtile.command.base import expose_command
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
        self.timezone = self._lift_timezone(self.timezone)

        if self.timezone is None:
            logger.debug("Defaulting to the system local timezone.")

    def _lift_timezone(self, timezone):
        if isinstance(timezone, tzinfo):
            return timezone
        elif isinstance(timezone, str):
            # Empty string can be used to force use of system time
            if not timezone:
                return None

            # A string timezone needs to be converted to a tzinfo object
            if "pytz" in sys.modules:
                return pytz.timezone(timezone)
            elif "dateutil" in sys.modules:
                return dateutil.tz.gettz(timezone)
            else:
                logger.warning(
                    "Clock widget can not infer its timezone from a"
                    " string without pytz or dateutil. Install one"
                    " of these libraries, or give it a"
                    " datetime.tzinfo instance."
                )
        elif timezone is None:
            pass
        else:
            logger.warning("Invalid timezone value %s.", timezone)

        return None

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

    @expose_command
    def update_timezone(self, timezone: str | tzinfo | None = None):
        """
        Force the clock to update timezone information.

        If the method is called with no arguments then the widget will reload
        the timzeone set on the computer (e.g. via ``timedatectl set-timezone ..``).
        This will have no effect if you have previously set a ``timezone`` value.

        Alternatively, you can pass a timezone string (e.g. ``"Europe/Lisbon"``) to change
        the specified timezone. Setting this to an empty string will cause the clock
        to rely on the system timezone.
        """
        self.timezone = self._lift_timezone(timezone)

        # Force python to update timezone info (e.g. if system time has changed)
        time.tzset()
        self.update(self.poll())

    @expose_command
    def use_system_timezone(self):
        """Force clock to use system timezone."""
        self.update_timezone("")
