from libqtile.widget import base

__all__ = ['She']


class She(base.InLoopPollText):
    ''' Widget to display the Super Hybrid Engine status.
    can display either the mode or CPU speed on eeepc computers.'''

    defaults = [
        ('device', '/sys/devices/platform/eeepc/cpufv', 'sys path to cpufv'),
        ('format', 'speed', 'Type of info to display "speed" or "name"'),
        ('update_interval', 0.5, 'Update Time in seconds.'),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, 'CPU', **config)
        self.add_defaults(She.defaults)
        self.modes = {
            '0x300': {'name': 'Performance', 'speed': '1.6GHz'},
            '0x301': {'name': 'Normal', 'speed': '1.2GHz'},
            '0x302': {'name': 'PoswerSave', 'speed': '800MHz'}
        }

    def poll(self):
        with open(self.device) as f:
            mode = f.read().strip()
        if self.mode in self.modes:
            return self.modes[mode][self.format]
        else:
            return mode
