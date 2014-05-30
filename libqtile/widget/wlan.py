import base
from pythonwifi.iwlibs import Wireless, Iwstats


class Wlan(base.InLoopPollText):
    """
        Displays Wifi ssid and quality.
    """
    defaults = [
        ('interface', 'wlan0', 'The interface to monitor'),
        ('update_interval', 1, 'The update interval.'),
    ]
    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Wlan.defaults)

    def poll(self):
        interface = Wireless(self.interface)
        stats = Iwstats(self.interface)
        quality = stats.qual.quality
        essid = interface.getEssid()
        return "{} {}/70".format(essid, quality)
