from . import base
from datetime import datetime, timedelta



class TeaTime(base.InLoopPollText):
    """
        A simple countdown timer text widget.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('format', 'Tea: {M}m {S}s',
            'Format of the displayed text. Available variables:'
            '{M} == minutes, {S} seconds.'),
        ('update_interval', 1., 'Update interval in seconds for the clock'),
        ('time', timedelta(minutes=6), "Time for the endo of the countdown"),
    ]

    def __init__(self, **config):
        super(TeaTime, self).__init__(**config)

    def poll(self):
        time = dict(M, S = divmod(self.time.seconds))
        return self.format.format(**time)
