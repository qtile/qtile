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
# Copyright (c) 2022 Hiago De Franco
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

from libqtile.log_utils import logger
from libqtile.widget import base


def get_status(interface_name):

    try:
        with open("/sys/class/net/" + interface_name + "/carrier") as fcarrier:
            cable_status = fcarrier.readline().rstrip("\n")
        with open("/sys/class/net/" + interface_name + "/operstate") as fstate:
            eth_status = fstate.readline().rstrip("\n")
    except FileNotFoundError:
        return None, None

    return cable_status, eth_status


class Eth(base.InLoopPollText):
    """
    Displays Ethernet status.

    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("interface", "eth0", "The interface to monitor"),
        ("update_interval", 1, "The update interval."),
        (
            "cable_disconnected_msg",
            "Disconnected",
            "String to show when the eth cable is disconnected.",
        ),
        ("cable_connected_msg", "Connected", "String to show when the eth cable is connected."),
        ("eth_down_msg", "Down", "String to show when the eth connection is down."),
        ("eth_up_msg", "Up", "String to show when the eth connection is down."),
        ("show_eth_msg", True, "Wether show or not the eth down and up messages."),
        (
            "format",
            "{cable_msg} {eth_msg}",
            'Display format."',
        ),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Eth.defaults)

    def poll(self):
        try:
            cable_status, eth_status = get_status(self.interface)

            # From kernel docs https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-net:
            # Carrier:
            # == =====================
            # 0  physical link is down
            # 1  physical link is up
            # == =====================
            # Operstate
            # Possible values are:
            # "unknown", "notpresent", "down", "lowerlayerdown", "testing",
            # "dormant", "up".

            # If None or cable disconnected, show disconnected message
            if (cable_status is None) or (eth_status is None) or (cable_status == "0"):
                return self.cable_disconnected_msg

            if self.show_eth_msg:
                if eth_status == "up":
                    self.eth_msg = self.eth_up_msg
                elif eth_status == "down":
                    self.eth_msg = self.eth_down_msg
                else:
                    self.eth_msg = eth_status
            else:
                self.eth_msg = None

            return self.format.format(cable_msg=self.cable_connected_msg, eth_msg=self.eth_msg)

        except EnvironmentError:
            logger.error(
                "%s: Probably your eth device is switched off or "
                " otherwise not present in your system.",
                self.__class__.__name__,
            )
