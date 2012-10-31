import cairo
import os
from libqtile import bar, manager
import base

BACKLIGHT_DIR = '/sys/class/backlight'

FORMAT = '{percent:2.0%}'

class Backlight(base._TextBox):
    """
        A simple widget to show the current brightness of a monitor.
    """

    filenames = {}

    defaults = manager.Defaults(
        ('font', 'Arial', 'Text font'),
        ('fontsize', None, 'Font pixel size. Calculated if None.'),
        ('padding', 3, 'Padding left and right. Calculated if None.'),
        ('background', None, 'Background colour.'),
        ('foreground', '#ffffff', 'Foreground colour.'),
        ('backlight_name', 'acpi_video0', 'ACPI name of a backlight device'),
        ('brightness_file', 'brightness', 'Name of file with the '
         'current brightness in /sys/class/backlight/backlight_name'),
        ('max_brightness_file', 'max_brightness', 'Name of file with the '
         'maximum brightness in /sys/class/backlight/backlight_name'),
        ('update_delay', .2, 'The delay in seconds between updates'),
    )

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "LIGHT", **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_delay, self.update)

    def _load_file(self, name):
        try:
            path = os.path.join(BACKLIGHT_DIR, self.backlight_name, name)
            with open(path, 'r') as f:
                return f.read().strip()
        except IOError:
            return False
        except Exception:
            self.log.exception("Failed to get %s" % name)

    def _get_info(self):
        try:
            info = {
                'brightness': float(self._load_file(self.brightness_file)),
                'max': float(self._load_file(self.max_brightness_file)),
                }
        except TypeError:
            return False
        return info

    def _get_text(self):
        info = self._get_info()
        if info == False:
            return 'Error'

        percent = info['brightness'] / info['max']
        return FORMAT.format(percent=percent)

    def update(self):
        ntext = self._get_text()
        if ntext != self.text:
            self.text = ntext
            self.bar.draw()
        return True
