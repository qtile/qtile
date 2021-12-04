from libqtile.widget import base
from libqtile.log_utils import logger


class ThermalZone(base.ThreadPoolText):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 2.0, 'Update interval'),
        ('zone', '/sys/class/thermal/thermal_zone0/temp', 'Thermal zone'),
        ('format', '{temp}°C', 'Thermal zone display format'),
        ('fgcolor_crit', 'ff0000', 'Font color on critical values'),
        ('fgcolor_high', 'ffaa00', 'Font color on high values'),
        ('fgcolor_normal', 'ffffff', 'Font color on normal values'),
        ('crit', 70, 'Critical temperature level'),
        ('high', 50, 'High themperature level'),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def poll(self):
        try:
            with open(self.zone) as f:
                value = round(int(f.read().rstrip()) / 1000)
                if value < self.high:
                    self.layout.colour = self.fgcolor_normal
                elif value in range(self.high, self.crit):
                    self.layout.colour = self.fgcolor_high
                elif value > self.crit:
                    self.layout.colour = self.fgcolor_crit
                variables = dict()
                variables['temp'] = str(value)
            return self.format.format(**variables)
        except OSError:
            logger.exception('{} does not exist'.format(self.zone))
            return 'err!'
