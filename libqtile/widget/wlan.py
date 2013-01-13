from .. import hook, bar
import base
from pythonwifi.iwlibs import Wireless, Iwstats

class Wlan(base._TextBox):
    """
        Displays Wifi ssid and quality.
    """
    def __init__(self, interface="wlan0", width=bar.CALCULATED, **config):
        """
            - interface: Wlan interface name.

            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.interface = interface
        base._TextBox.__init__(self, " ", width, **config)
        self.timeout_add(1, self.update)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

    def update(self):
        if self.configured:
            interface = Wireless(self.interface)
            stats = Iwstats(self.interface)
            quality = stats.qual.quality
            essid = interface.getEssid()
            text = "{} {}/70".format(essid, quality)
            if self.text != text:
                self.text = text
                self.bar.draw()
        return True
