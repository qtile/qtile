from os import path
from libqtile.widget import base
from libqtile.log_utils import logger

class ThermalZone(base.ThreadPoolText):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 2.0, 'Update interval for the thermal zone sensor'),
        ('zone', '/sys/class/thermal/thermal_zone0/temp', 'Default thermal zone'),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def poll(self):
        if path.isfile(self.zone):
            with open(self.zone) as f:
                value = str(round(int(f.read().rstrip()) / 1000)) + '°C'
            return value
        else:
            logger.exception('{} does not exist'.format(self.zone))
            return 'err!'

