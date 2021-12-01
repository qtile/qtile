from os import path
from libqtile.widget import base
from libqtile.log_utils import logger

class ThermalZone(base.ThreadPoolText):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 2.0, 'Update interval for the thermal zone sensor'),
        ('zone', '0', 'Default thermal zone'),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def poll(self):
        zone = '/sys/class/thermal/thermal_zone' + self.zone + '/temp'
        if path.isfile(zone):
            with open(zone) as f:
                value = str(round(int(f.read().rstrip()) / 1000)) + '°C'
            return value
        else:
            logger.exception('{} does not exist'.format(zone))
            return 'err!'

