from libqtile.widget import base

class ThermalZone(base.ThreadPoolText):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 2.0, 'Update interval for the thermal zone sensor'),
        ('zone', '0', 'Default thermal zone'),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def get_temp(self):
        with open('/sys/class/thermal/thermal_zone' + self.zone + '/temp') as f:
            value = str(round(int(f.read().rstrip()) / 1000)) + '°C'
        return value

    def poll(self):
        temp_values = self.get_temp()
        return temp_values

