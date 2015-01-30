from datetime import datetime

import base


class Countdown(base.InLoopPollText):
    """
        A simple countdown timer text widget.
    """

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
