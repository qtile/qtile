import os

from .. import bar, hook, manager
import base

class Battery(base._TextBox):
    """
        A simple but flexible text-based clock.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "BAT", **config)
        self.bat = BatteryReader(BAT_DIR)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.tick(self.update)

    def update(self):
        stat = self.bat.stat()

        if stat == DISCHARGING:
            self.text = 'V {0:2.2f}%'.format(self.bat.percent())
        elif stat == CHARGING:
            self.text = '^ {0:2.2f}%'.format(self.bat.percent())
        else:
            self.text = 'Full'
        # following line bumps up cpu to 80%
        #self.bar.draw()



class BatteryReader(object):
    """Battery using functions eats 80% of cpu see if you hold a file
    handle if it improves"""

    def __init__(self, path):
        self.path = path
        self.stat_fin = open(os.path.join(self.path, 'status'))
        self.now_fin = open(os.path.join(self.path, 'energy_now'))
        self.full_fin = open(os.path.join(self.path, 'energy_full'))

    def stat(self):
        self.stat_fin.seek(0)
        return self.stat_fin.read().strip()

    def percent(self):
        self.now_fin.seek(0)
        self.full_fin.seek(0)
        return 100 * float(self.now_fin.read())/float(self.full_fin.read())

BAT_DIR = '/sys/class/power_supply/BAT0/'
CHARGING = 'Charging'
DISCHARGING = 'Discharging'
UNKNOWN = 'Unknown'

def status():
    return _read_file('status')


def current_charge():
    return float(_read_file('energy_now'))


def capacity():
    return float(_read_file('energy_full'))


def _read_file(x):
    return open(os.path.join(BAT_DIR, x)).read().strip()


def percent():
    return current_charge()/capacity()


def info():
    stat = status()
    if stat == CHARGING:
        return 'charging'
    elif stat == DISCHARGING:
        
        return 'discharging'
    else:
        return 'a/c'
