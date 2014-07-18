from datetime import datetime

import base


class Countdown(base.InLoopPollText):
    """
        A simple countdown text widget.
    """

    defaults = [
        ('format', '{D}d {H}h {M}m {S}s',
            'string formating: "{D}d {H}h {M}m {S}s" for 01d 10h 42m 21s'),
        ('update_interval', 1., 'Update interval for the clock'),
    ]

    def __init__(self, date, **config):
        """
            - date: a datetime with the end of the countdown
        """

        self.date = date
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
