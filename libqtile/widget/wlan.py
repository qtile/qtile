import iwlib

from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.wlaniw import process_essid_and_quality


def get_status(interface_name: str):
    interface = iwlib.get_iwconfig(interface_name)
    if "stats" not in interface:
        return None, None

    quality = interface["stats"]["quality"]
    if not isinstance(quality, int):
        quality = None

    essid = bytes(interface["ESSID"]).decode()

    return essid, quality


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
        self.ethernet_interface_not_found = False

    def poll(self):
        essid, quality = get_status(self.interface)
        return process_essid_and_quality(
            self,
            essid=essid,
            quality=quality,
        )
