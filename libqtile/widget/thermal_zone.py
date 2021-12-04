from libqtile.widget import base
from libqtile.log_utils import logger


class ThermalZone(base.ThreadPoolText):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 2.0, 'Update interval for the thermal zone sensor'),
        ('zone', '/sys/class/thermal/thermal_zone0/temp', 'Default thermal zone'),
        ('format', '{temp}°C', 'Thermal zone display format'),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def poll(self):
        try:
            with open(self.zone) as f:
                variables = dict()
                variables['temp'] = str(round(int(f.read().rstrip()) / 1000))
            return self.format.format(**variables)
        except OSError:
            logger.exception('{} does not exist'.format(self.zone))
            return 'err!'
