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

from libqtile.log_utils import logger
from libqtile.widget import base


def wifi_get_status(interface_name):
    interface = iwlib.get_iwconfig(interface_name)
    if "stats" not in interface:
        return None, None
    quality = interface["stats"]["quality"]
    essid = bytes(interface["ESSID"]).decode()
    return essid, quality


def eth_get_status(interface_name):
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
    try:
        with open("/sys/class/net/" + interface_name + "/carrier") as fcarrier:
            cable_status = fcarrier.readline().rstrip("\n")
        with open("/sys/class/net/" + interface_name + "/operstate") as fstate:
            link_status = fstate.readline().rstrip("\n")
    except FileNotFoundError:
        return None, None
    return cable_status, link_status


class Wlan(base.InLoopPollText):
    """
    Displays Wifi SSID and quality. If `show_eth` is True, also shows Ethernet information.

    Widget requirements: iwlib_.

    .. _iwlib: https://pypi.org/project/iwlib/
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("show_wifi", True, "Show WiFi information."),
        ("wifi_interface", "wlan0", "The wifi interface to monitor"),
        ("update_interval", 1, "The update interval."),
        ("wifi_disc_msg", "Disconnected", "String to show when the wlan is diconnected."),
        (
            "format_wifi",
            "{essid} {quality}/70",
            'Display format for wifi_interface. For percents you can use "{essid} {percent:2.0%}"',
        ),
        (
            "show_eth",
            False,
            'Show Ethernet information. It\'ll be displayed alongside the WiFi with a "separator" if "show_wifi" is also set.',
        ),
        ("eth_interface", "eth0", "The eth interface to monitor"),
        (
            "separator",
            " | ",
            "Separator between Ethernet and WiFi information (if show_eth is True).",
        ),
        (
            "eth_disc_msg",
            "Disconnected",
            "String to show when the eth is disconnected (cable not connected).",
        ),
        (
            "eth_cable_con_msg",
            "1",
            "String to show when the Ethernet is connected. The default is '1' for connected.",
        ),
        (
            "format_eth",
            "{cable_status} {link_status}",
            "Display format for eth interface.",
        ),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Wlan.defaults)

    def poll(self):
        data = {
            "essid": None,
            "quality": None,
            "cable_status": None,
            "link_status": None,
        }
        try:
            essid, quality = wifi_get_status(self.wifi_interface)
            if essid is not None:
                data["essid"] = essid
                data["quality"] = quality
        except EnvironmentError:
            logger.error(
                "%s: Probably your wlan device is switched off or "
                " otherwise not present in your system.",
                self.__class__.__name__,
            )
        try:
            cable_status, link_status = eth_get_status(self.eth_interface)
            if cable_status is not None:
                data["cable_status"] = cable_status
                data["link_status"] = link_status
        except EnvironmentError:
            logger.error(
                "%s: Probably your wlan device is switched off or "
                " otherwise not present in your system.",
                self.__class__.__name__,
            )
        return self.build_string(data)

    def build_string(self, data):
        full_msg = ""

        # Case show both interfaces
        if self.show_wifi and self.show_eth:
            if data["essid"] is None:
                full_msg += self.wifi_disc_msg
            else:
                full_msg += self.format_wifi.format(
                    essid=data["essid"], quality=data["quality"], percent=(data["quality"] / 70)
                )

            if (data["cable_status"] is None) or (data["cable_status"] == "0"):
                full_msg += self.separator + self.eth_disc_msg
            else:
                full_msg += self.separator + self.format_eth.format(
                    cable_status=self.eth_cable_con_msg, link_status=data["link_status"]
                )

            return full_msg

        # Case show only WiFi interface
        elif self.show_wifi and not self.show_eth:
            if data["essid"] is None:
                full_msg += self.wifi_disc_msg
            else:
                full_msg += self.format_wifi.format(
                    essid=data["essid"], quality=data["quality"], percent=(data["quality"] / 70)
                )

            return full_msg

        # Case show only Ethernet interface
        elif not self.show_wifi and self.show_eth:
            if (data["cable_status"] is None) or (data["cable_status"] == "0"):
                full_msg += self.eth_disc_msg
            else:
                full_msg += self.format_eth.format(
                    cable_status=self.eth_cable_con_msg, link_status=data["link_status"]
                )

            return full_msg

        return "Both show_eth and show_wifi are disabled."
