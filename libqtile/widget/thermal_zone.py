from libqtile.log_utils import logger
from libqtile.widget import base


class ThermalZone(base.ThreadPoolText):
    """Thermal zone widget.

    This widget was made to read thermal zone files and transform values to
    human readable format. You can set zone parameter to any standard thermal
    zone file from /sys/class/thermal directory.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 2.0, "Update interval"),
        ("zone", "/sys/class/thermal/thermal_zone0/temp", "Thermal zone"),
        ("format", "{temp}°C", "Display format"),
        ("format_crit", "{temp}°C CRIT!", "Critical display format"),
        ("hidden", False, "Set True to only show if critical value reached"),
        ("fgcolor_crit", "ff0000", "Font color on critical values"),
        ("fgcolor_high", "ffaa00", "Font color on high values"),
        ("fgcolor_normal", "ffffff", "Font color on normal values"),
        ("crit", 70, "Critical temperature level"),
        ("high", 50, "High themperature level"),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(ThermalZone.defaults)

    def poll(self):
        try:
            with open(self.zone) as f:
                value = round(int(f.read().rstrip()) / 1000)
        except OSError:
            logger.exception("{} does not exist".format(self.zone))
            return "err!"

        variables = dict()
        variables["temp"] = str(value)
        output = self.format.format(**variables)
        if value < self.high:
            self.layout.colour = self.fgcolor_normal
        elif value < self.crit:
            self.layout.colour = self.fgcolor_high
        elif value >= self.crit:
            self.layout.colour = self.fgcolor_crit
            output = self.format_crit.format(**variables)
        if self.hidden and value < self.crit:
            output = ""
        return output
