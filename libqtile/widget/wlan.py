import re
import subprocess

from libqtile.log_utils import logger
from libqtile.pangocffi import markup_escape_text
from libqtile.widget import base

_IW_BACKEND = None
try:
    import iwlib

    _IW_BACKEND = "iwlib"

except ImportError:
    pass

if _IW_BACKEND is None:
    try:
        _ = subprocess.run(["iw", "--help"], stdout=subprocess.DEVNULL)
        _IW_BACKEND = "iw"

    except FileNotFoundError:
        pass

if _IW_BACKEND is None:
    logger.exception("Both iwlib could not be imported and iw could not be found in PATH.")


def _get_status_from_iwlib(interface_name: str):
    interface = iwlib.get_iwconfig(interface_name)
    if "stats" not in interface:
        return None, None
    quality = interface["stats"]["quality"]
    essid = bytes(interface["ESSID"]).decode()
    return essid, quality


def _get_status_from_iw(interface_name: str):
    try:
        result = subprocess.run(
            ["iw", "dev", interface_name, "link"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.exception(f"Could not get wifi status for {interface_name}:")
        return None, None

    output = result.stdout
    if "Not connected." in output:
        return None, None

    essid, quality = None, None
    for line in output.splitlines():
        line = line.strip()

        if line.startswith("SSID:"):
            essid = line.split("SSID:")[1].strip()

        elif line.startswith("signal:"):
            quality = int(line.split()[1])

            match = re.search(r"signal:\s*(-?\d+)", line)
            if match:
                quality = int(match.group(1))

            if quality < 0:
                quality *= -1

    if essid is None or quality is None:
        return None, None

    return essid, quality


def _get_status_from_none(*_, **__):
    return "N/A", "N/A"


def get_status(interface_name: str):
    if _IW_BACKEND == "iwlib":
        return _get_status_from_iwlib(interface_name)
    elif _IW_BACKEND == "iw":
        return _get_status_from_iw(interface_name)
    else:
        return _get_status_from_none(interface_name)


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
