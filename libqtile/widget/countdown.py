from datetime import datetime

from libqtile.widget import base


class Countdown(base.InLoopPollText):
    """A simple countdown timer text widget"""

    defaults = [
        (
            "format",
            "{D}d {H}h {M}m {S}s",
            "Format of the displayed text. Available variables:"
            "{D} == days, {H} == hours, {M} == minutes, {S} seconds.",
        ),
        ("update_interval", 1.0, "Update interval in seconds for the clock"),
        ("date", datetime.now(), "The datetime for the end of the countdown"),
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

        data = {
            "D": f"{days:02d}",
            "H": f"{hours:02d}",
            "M": f"{minutes:02d}",
            "S": f"{seconds:02d}",
        }

        return self.format.format(**data)
