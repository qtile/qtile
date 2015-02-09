# Copyright (c) 2012 Sebastian Bechtel
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2014 Craig Barnes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from . import base
import logging
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
        try:
            stats = Iwstats(self.interface)
            quality = stats.qual.quality
            essid = interface.getEssid()
            return "{} {}/70".format(essid, quality)
        except IOError:
            logging.getLogger('qtile').error('%s: Probably your wlan device '
                    'is switched off or otherwise not present in your system.',
                    self.__class__.__name__)
