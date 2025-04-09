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
import subprocess

import iwlib

from libqtile.log_utils import logger
from libqtile.pangocffi import markup_escape_text
from libqtile.widget import base


def get_status(interface_name):
    interface = iwlib.get_iwconfig(interface_name)
    if "stats" not in interface:
        return None, None
    quality = interface["stats"]["quality"]
    essid = bytes(interface["ESSID"]).decode()
    return essid, quality


def get_private_ip(interface_name):
    try:
        result = subprocess.run(
            ["ip", "-brief", "addr", "show", "dev", interface_name],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        logger.exception(f"Couldn't get the IP for {interface_name}:")
        return "N/A"

    output = result.stdout.strip()
    parts = output.split()
    if len(parts) > 2 and parts[1] == "UP":
        ip_address = parts[2].split("/")[0]
        if ":" not in ip_address:
            return ip_address

    return "N/A"


class Wlan(base.InLoopPollText):
    """
    Displays Wifi SSID and quality.

    Widget requirements: iwlib_.

    .. _iwlib: https://pypi.org/project/iwlib/
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("interface", "wlan0", "The interface to monitor"),
        (
            "ethernet_interface",
            "eth0",
            "The ethernet interface to monitor, NOTE: If you do not have a wlan device in your system, ethernet functionality will not work, use the Net widget instead",
        ),
        ("update_interval", 1, "The update interval."),
        ("disconnected_message", "Disconnected", "String to show when the wlan is diconnected."),
        (
            "ethernet_message_format",
            "eth",
            "String to show when ethernet is being used. For IP of ethernet interface use {ipaddr}.",
        ),
        (
            "use_ethernet",
            False,
            "Activate or deactivate checking for ethernet when no wlan connection is detected",
        ),
        (
            "format",
            "{essid} {quality}/70",
            'Display format. For percents you can use "{essid} {percent:2.0%}". For IP of wlan interface use {ipaddr}.',
        ),
    ]

    def __init__(self, **config):
        if "ethernet_message" in config:
            logger.warning(
                "`ethernet_message` parameter is deprecated. Please rename to `ethernet_message_format`"
            )
            config["ethernet_message_format"] = config.pop("ethernet_message")
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Wlan.defaults)
        self.ethernetInterfaceNotFound = False

    def poll(self):
        try:
            essid, quality = get_status(self.interface)
            disconnected = essid is None
            ipaddr = "N/A"
            if not disconnected:
                ipaddr = get_private_ip(self.interface)
            else:
                if self.use_ethernet:
                    ipaddr = get_private_ip(self.ethernet_interface)
                    try:
                        with open(
                            f"/sys/class/net/{self.ethernet_interface}/operstate"
                        ) as statfile:
                            if statfile.read().strip() == "up":
                                return self.ethernet_message_format.format(ipaddr=ipaddr)
                            else:
                                return self.disconnected_message
                    except FileNotFoundError:
                        if not self.ethernetInterfaceNotFound:
                            logger.error("Ethernet interface has not been found!")
                            self.ethernetInterfaceNotFound = True
                        return self.disconnected_message
                else:
                    return self.disconnected_message
            return self.format.format(
                essid=markup_escape_text(essid),
                quality=quality,
                percent=(quality / 70),
                ipaddr=ipaddr,
            )
        except OSError:
            logger.error(
                "Probably your wlan device is switched off or "
                " otherwise not present in your system."
            )
