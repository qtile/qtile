# -*- coding: utf-8 -*-
# Copyright (c) 2012 Sebastian Bechtel
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2014 Craig Barnes
# Copyright (c) 2015 farebord
# Copyright (c) 2015 Jörg Thalheim (Mic92)
# Copyright (c) 2016 Juhani Imberg
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
import iwlib

from . import base
from libqtile.log_utils import logger


def get_status(interface_name):
    interface = iwlib.get_iwconfig(interface_name)
    if 'stats' not in interface:
        return None, None
    quality = interface['stats']['quality']
    essid = bytes(interface['ESSID']).decode()
    return essid, quality


class Wlan(base.InLoopPollText):
    """
    Displays Wifi SSID and quality.

    Widget requirements: iwlib_.

    .. _iwlib: https://pypi.org/project/iwlib/
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('interface', 'wlan0', 'The interface to monitor'),
        ('update_interval', 1, 'The update interval.'),
        (
            'disconnected_message',
            'Disconnected',
            'String to show when the wlan is diconnected.'
        ),
        (
            'format',
            '{essid} {quality}/70',
            'Display format. For percents you can use "{essid} {percent:2.0%}"'
        )
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Wlan.defaults)

    def poll(self):
        try:
            essid, quality = get_status(self.interface)
            disconnected = essid is None
            if disconnected:
                return self.disconnected_message

            return self.format.format(
                essid=essid,
                quality=quality,
                percent=(quality / 70)
            )
        except EnvironmentError:
            logger.error(
                '%s: Probably your wlan device is switched off or '
                ' otherwise not present in your system.',
                self.__class__.__name__)
