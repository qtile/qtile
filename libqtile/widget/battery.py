import os

from .. import bar, hook, manager
import base

BAT_DIR = '/sys/class/power_supply'
CHARGING = 'Charging'
DISCHARGING = 'Discharging'
UNKNOWN = 'Unknown'

class Battery(base._TextBox):
    """
        A simple but flexible text-based battery widget.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Battery widget font"),
        ("fontsize", None, "Battery widget pixel size. Calculated if None."),
        ("padding", None, "Battery widget padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour"),
        ("low_foreground", "FF0000", "font when battery is low"),
        ("format", "{char} {percent:2.0%} {hour:d}:{min:02d}", "Display format"),
        ("battery_name", "BAT0", "ACPI name of a battery, usually BAT0"),
        ("status_file", "status", "Name of status file in /sys/class/power_supply/battery_name"),
        ("energy_now_file", "energy_now", "Name of file with the current energy in /sys/class/power_supply/battery_name"),
        ("energy_full_file", "energy_full", "Name of file with the maximum energy in /sys/class/power_supply/battery_name"),
        ("power_now_file", "power_now", "Name of file with the current power draw in /sys/class/power_supply/battery_name"),
        ("update_delay",1,"The delay in seconds between updates"),
        ("charge_char","^","Character to indicate the battery is charging"),
        ("discharge_char","V","Character to indicate the battery is discharging"),

    )
    def __init__(self, low_percentage=0.10, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "BAT", **config)
        self.low_percentage = low_percentage

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_delay, self.update)

    def _get_info(self):
        try:
            stat = self._get_param(self.status_file)
            now = float(self._get_param(self.energy_now_file))
            full = float(self._get_param(self.energy_full_file))
            power = float(self._get_param(self.power_now_file))
        except IOError:
            return "Battery files not found"

        try:
            if stat == DISCHARGING:
                char = self.discharge_char
                time = now/power
            elif stat == CHARGING:
                char = self.charge_char
                time = (full - now)/power
            else:
                return 'Full'
        except ZeroDivisionError:
            return 'Inf'

        hour = int(time)
        min = int(time*60) % 60
        percent = now / full
        if stat == DISCHARGING and percent < self.low_percentage:
            self.layout.colour = self.low_foreground
        else:
            self.layout.colour = self.foreground
        return self.format.format(char=char,
                           percent=percent,
                           hour=hour, min=min)

    def update(self):
        ntext = self._get_info()
        if ntext != self.text:
            self.text = ntext
            self.bar.draw()
        return True

    def _get_param(self, name):
        with open(os.path.join(BAT_DIR, self.battery_name, name), 'r') as f:
            return f.read().strip()
