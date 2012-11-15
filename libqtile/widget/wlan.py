from .. import hook, bar, manager
import base
from pythonwifi.iwlibs import Wireless, Iwstats

class Wlan(base._TextBox):
    """
        Displays Wifi ssid and quality.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Font"),
        ("fontsize", None, "Pixel size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
    def __init__(self, interface="wlan0", width=bar.CALCULATED, **config):
        """
            - interface: Wlan interface name.

            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.interface = interface
        base._TextBox.__init__(self, " ", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(1, self.update)

    def update(self):
        interface = Wireless(self.interface)
        stats = Iwstats(self.interface)
        quality = stats.qual.quality
        essid = interface.getEssid()
        text = "{} {}/70".format(essid, quality)
        if self.text != text:
            self.text = text
            self.bar.draw()
        return True

