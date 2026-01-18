import re
import subprocess

from libqtile.log_utils import logger
from libqtile.pangocffi import markup_escape_text
from libqtile.widget.generic_poll_text import GenPollCommand


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


def parse_iw_output(raw: str):
    essid, quality = None, None
    for line in raw.splitlines():
        line = line.strip()

        if line.startswith("SSID:"):
            essid_match = re.search(r"SSID:\s*(.*)", line)
            if essid_match is not None:
                essid = essid_match.group(1)
                if not isinstance(essid, str):
                    essid = None

        elif line.startswith("signal:"):
            signal_match = re.search(r"signal:\s*(-?\d+)", line)
            if signal_match:
                signal_str = signal_match.group(1)
                signal = int(signal_str)
                if signal.__str__() != signal_str:
                    quality = None
                else:
                    # see: https://superuser.com/questions/866005/wireless-connection-link-quality-what-does-31-70-indicate
                    quality = signal + 110

    return essid, quality


def process_essid_and_quality(
    self,
    essid: str | None,
    quality: int | None,
):
    """
    The polling and parsing logic for both Wlan and WlanIw respectively. See
    libqtile.widget.wlan.Wlan.poll and libqtile.widget.wlaniw.WlanIw.parse.
    """

    try:
        disconnected = essid is None
        quality = 0 if quality is None else quality

        ipaddr = "N/A"
        if not disconnected:
            ipaddr = get_private_ip(self.interface)

        else:
            if self.use_ethernet:
                ipaddr = get_private_ip(self.ethernet_interface)
                try:
                    with open(f"/sys/class/net/{self.ethernet_interface}/operstate") as statfile:
                        if statfile.read().strip() == "up":
                            return self.ethernet_message_format.format(ipaddr=ipaddr)

                        else:
                            return self.disconnected_message

                except FileNotFoundError:
                    if not self.ethernet_interface_not_found:
                        logger.error("Ethernet interface has not been found!")
                        self.ethernet_interface_not_found = True
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
            "Probably your wlan device is switched off or  otherwise not present in your system."
        )


class WlanIw(GenPollCommand):
    defaults = [
        ("interface", "wlan0", "The interface to monitor"),
        (
            "ethernet_interface",
            "eth0",
            "The ethernet interface to monitor, NOTE: If you do not have a wlan device in your system, ethernet functionality will not work, use the Net widget instead",
        ),
        ("update_interval", 1, "The update interval."),
        (
            "disconnected_message",
            "Disconnected",
            "String to show when the wlan is diconnected.",
        ),
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
        interface = config.get("interface", None)
        interface = interface if interface is not None else "wlan0"
        config["cmd"] = ["iw", "dev", interface, "link"]
        super().__init__(**config)
        self.add_defaults(WlanIw.defaults)
        self.ethernet_interface_not_found = False

    def parse(self, raw: str):
        essid, quality = parse_iw_output(raw)
        return process_essid_and_quality(
            self,
            essid=essid,
            quality=quality,
        )
