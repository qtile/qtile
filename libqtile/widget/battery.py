# Copyright (c) 2011 matt
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2011-2014 Tycho Andersen
# Copyright (c) 2012 dmpayton
# Copyright (c) 2012 hbc
# Copyright (c) 2012 Tim Neumann
# Copyright (c) 2012 uberj
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Sebastien Blot
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

from __future__ import annotations

import os
import platform
import re
import warnings
from abc import ABC, abstractclassmethod
from enum import Enum, unique
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, NamedTuple

from libqtile import bar, configurable, images
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.utils import send_notification
from libqtile.widget import base

if TYPE_CHECKING:
    from typing import Any

    from libqtile.utils import ColorsType


@unique
class BatteryState(Enum):
    CHARGING = 1
    DISCHARGING = 2
    FULL = 3
    EMPTY = 4
    UNKNOWN = 5


BatteryStatus = NamedTuple(
    "BatteryStatus",
    [
        ("state", BatteryState),
        ("percent", float),
        ("power", float),
        ("time", int),
    ],
)


class _Battery(ABC):
    """
    Battery interface class specifying what member functions a
    battery implementation should provide.
    """

    @abstractclassmethod
    def update_status(self) -> BatteryStatus:
        """Read the battery status

        Reads the battery status from the system and returns the result.

        Raises RuntimeError on error.
        """
        pass


def load_battery(**config) -> _Battery:
    """Default battery loading function

    Loads and returns the _Battery interface suitable for the current running
    platform.

    Parameters
    ----------
    config: Dictionary of config options that are passed to the generated
    battery.

    Return
    ------
    The configured _Battery for the current platform.
    """
    system = platform.system()
    if system == "FreeBSD":
        return _FreeBSDBattery(str(config["battery"]))
    elif system == "Linux":
        return _LinuxBattery(**config)
    else:
        raise RuntimeError("Unknown platform!")


class _FreeBSDBattery(_Battery):
    """
    A battery class compatible with FreeBSD. Reads battery status
    using acpiconf.

    Takes a battery setting containing the number of the battery
    that should be monitored.
    """

    def __init__(self, battery="0") -> None:
        self.battery = battery

    def update_status(self) -> BatteryStatus:
        try:
            info = check_output(["acpiconf", "-i", self.battery]).decode("utf-8")
        except CalledProcessError:
            raise RuntimeError("acpiconf exited incorrectly")

        stat_match = re.search(r"State:\t+([a-z]+)", info)

        if stat_match is None:
            raise RuntimeError("Could not get battery state!")

        stat = stat_match.group(1)
        if stat == "charging":
            state = BatteryState.CHARGING
        elif stat == "discharging":
            state = BatteryState.DISCHARGING
        elif stat == "high":
            state = BatteryState.FULL
        else:
            state = BatteryState.UNKNOWN

        percent_re = re.search(r"Remaining capacity:\t+([0-9]+)", info)
        if percent_re:
            percent = int(percent_re.group(1)) / 100
        else:
            raise RuntimeError("Could not get battery percentage!")

        power_re = re.search(r"Present rate:\t+(?:[0-9]+ mA )*\(?([0-9]+) mW", info)
        if power_re:
            power = float(power_re.group(1)) / 1000
        else:
            raise RuntimeError("Could not get battery power!")

        time_re = re.search(r"Remaining time:\t+([0-9]+:[0-9]+|unknown)", info)
        if time_re:
            if time_re.group(1) == "unknown":
                time = 0
            else:
                hours, _, minutes = time_re.group(1).partition(":")
                time = int(hours) * 3600 + int(minutes) * 60
        else:
            raise RuntimeError("Could not get remaining battery time!")

        return BatteryStatus(state, percent=percent, power=power, time=time)


class _LinuxBattery(_Battery, configurable.Configurable):
    defaults = [
        ("status_file", None, "Name of status file in /sys/class/power_supply/battery_name"),
        (
            "energy_now_file",
            None,
            "Name of file with the current energy in /sys/class/power_supply/battery_name",
        ),
        (
            "energy_full_file",
            None,
            "Name of file with the maximum energy in /sys/class/power_supply/battery_name",
        ),
        (
            "power_now_file",
            None,
            "Name of file with the current power draw in /sys/class/power_supply/battery_name",
        ),
    ]

    filenames = {}  # type: dict

    BAT_DIR = "/sys/class/power_supply"

    BATTERY_INFO_FILES = {
        "energy_now_file": ["energy_now", "charge_now"],
        "energy_full_file": ["energy_full", "charge_full"],
        "power_now_file": ["power_now", "current_now"],
        "voltage_now_file": ["voltage_now"],
        "status_file": ["status"],
    }

    def __init__(self, **config):
        _LinuxBattery.defaults.append(
            ("battery", self._get_battery_name(), "ACPI name of a battery, usually BAT0")
        )

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_LinuxBattery.defaults)
        if isinstance(self.battery, int):
            self.battery = "BAT{}".format(self.battery)

    def _get_battery_name(self):
        if os.path.isdir(self.BAT_DIR):
            bats = [f for f in os.listdir(self.BAT_DIR) if f.startswith("BAT")]
            if bats:
                return bats[0]
        return "BAT0"

    def _load_file(self, name) -> tuple[str, str] | None:
        path = os.path.join(self.BAT_DIR, self.battery, name)
        if "energy" in name or "power" in name:
            value_type = "uW"
        elif "charge" in name:
            value_type = "uAh"
        elif "current" in name:
            value_type = "uA"
        else:
            value_type = ""

        try:
            with open(path, "r") as f:
                return f.read().strip(), value_type
        except OSError as e:
            logger.debug("Failed to read '{}': {}".format(path, e))
            if isinstance(e, FileNotFoundError):
                # Let's try another file if this one doesn't exist
                return None
            # Do not fail if the file exists but we can not read it this time
            # See https://github.com/qtile/qtile/pull/1516 for rationale
            return "-1", "N/A"

    def _get_param(self, name) -> tuple[str, str]:
        if name in self.filenames and self.filenames[name]:
            result = self._load_file(self.filenames[name])
            if result is not None:
                return result

        # Don't have the file name cached, figure it out
        # Don't modify the global list! Copy with [:]
        file_list = self.BATTERY_INFO_FILES.get(name, [])[:]
        user_file_name = getattr(self, name, None)
        if user_file_name is not None:
            file_list.insert(0, user_file_name)

        # Iterate over the possibilities, and return the first valid value
        for filename in file_list:
            value = self._load_file(filename)
            if value is not None:
                self.filenames[name] = filename
                return value

        raise RuntimeError("Unable to read status for {}".format(name))

    def update_status(self) -> BatteryStatus:
        stat = self._get_param("status_file")[0]

        if stat == "Full":
            state = BatteryState.FULL
        elif stat == "Charging":
            state = BatteryState.CHARGING
        elif stat == "Discharging":
            state = BatteryState.DISCHARGING
        else:
            state = BatteryState.UNKNOWN

        now_str, now_unit = self._get_param("energy_now_file")
        full_str, full_unit = self._get_param("energy_full_file")
        power_str, power_unit = self._get_param("power_now_file")
        # the units of energy is uWh or uAh, multiply to get to uWs or uAs
        now = 3600 * float(now_str)
        full = 3600 * float(full_str)
        power = float(power_str)

        if now_unit != full_unit:
            raise RuntimeError("Current and full energy units do not match")
        if full == 0:
            percent = 0.0
        else:
            percent = now / full

        if power == 0:
            time = 0
        elif state == BatteryState.DISCHARGING:
            time = int(now / power)
        else:
            time = int((full - now) / power)

        if power_unit == "uA":
            voltage = float(self._get_param("voltage_now_file")[0])
            power = voltage * power / 1e12
        elif power_unit == "uW":
            power = power / 1e6

        return BatteryStatus(state=state, percent=percent, power=power, time=time)


class Battery(base.ThreadPoolText):
    """A text-based battery monitoring widget currently supporting FreeBSD"""

    background: ColorsType | None
    low_background: ColorsType | None

    defaults = [
        ("charge_char", "^", "Character to indicate the battery is charging"),
        ("discharge_char", "V", "Character to indicate the battery is discharging"),
        ("full_char", "=", "Character to indicate the battery is full"),
        ("empty_char", "x", "Character to indicate the battery is empty"),
        ("unknown_char", "?", "Character to indicate the battery status is unknown"),
        ("format", "{char} {percent:2.0%} {hour:d}:{min:02d} {watt:.2f} W", "Display format"),
        ("hide_threshold", None, "Hide the text when there is enough energy 0 <= x < 1"),
        ("show_short_text", True, 'Show "Full" or "Empty" rather than formated text'),
        ("low_percentage", 0.10, "Indicates when to use the low_foreground color 0 < x < 1"),
        ("low_foreground", "FF0000", "Font color on low battery"),
        ("low_background", None, "Background color on low battery"),
        ("update_interval", 60, "Seconds between status updates"),
        ("battery", 0, "Which battery should be monitored (battery number or name)"),
        ("notify_below", None, "Send a notification below this battery level."),
        ("notification_timeout", 10, "Time in seconds to display notification. 0 for no expiry."),
    ]

    def __init__(self, **config) -> None:
        if "update_delay" in config:
            warnings.warn(
                "Change from using update_delay to update_interval for battery widget, removed in 0.15",
                DeprecationWarning,
            )
            config["update_interval"] = config.pop("update_delay")

        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(self.defaults)

        self._battery = self._load_battery(**config)
        self._has_notified = False
        self.timeout = int(self.notification_timeout * 1000)

    def _configure(self, qtile, bar):
        if not self.low_background:
            self.low_background = self.background
        self.normal_background = self.background

        base.ThreadPoolText._configure(self, qtile, bar)

    @staticmethod
    def _load_battery(**config):
        """Function used to load the Battery object

        Battery behavior can be changed by overloading this function in a base
        class.
        """
        return load_battery(**config)

    def poll(self) -> str:
        """Determine the text to display

        Function returning a string with battery information to display on the
        status bar. Should only use the public interface in _Battery to get
        necessary information for constructing the string.
        """
        try:
            status = self._battery.update_status()
        except RuntimeError as e:
            return "Error: {}".format(e)

        if self.notify_below:
            percent = int(status.percent * 100)
            if percent < self.notify_below:
                if not self._has_notified:
                    send_notification(
                        "Warning",
                        "Battery at {0}%".format(percent),
                        urgent=True,
                        timeout=self.timeout,
                    )
                    self._has_notified = True
            elif self._has_notified:
                self._has_notified = False

        return self.build_string(status)

    def build_string(self, status: BatteryStatus) -> str:
        """Determine the string to return for the given battery state

        Parameters
        ----------
        status:
            The current status of the battery

        Returns
        -------
        str
            The string to display for the current status.
        """
        if self.hide_threshold is not None and status.percent > self.hide_threshold:
            return ""

        if self.layout is not None:
            if status.state == BatteryState.DISCHARGING and status.percent < self.low_percentage:
                self.layout.colour = self.low_foreground
                self.background = self.low_background
            else:
                self.layout.colour = self.foreground
                self.background = self.normal_background

        if status.state == BatteryState.CHARGING:
            char = self.charge_char
        elif status.state == BatteryState.DISCHARGING:
            char = self.discharge_char
        elif status.state == BatteryState.FULL:
            if self.show_short_text:
                return "Full"
            char = self.full_char
        elif status.state == BatteryState.EMPTY or (
            status.state == BatteryState.UNKNOWN and status.percent == 0
        ):
            if self.show_short_text:
                return "Empty"
            char = self.empty_char
        else:
            char = self.unknown_char

        hour = status.time // 3600
        minute = (status.time // 60) % 60

        return self.format.format(
            char=char, percent=status.percent, watt=status.power, hour=hour, min=minute
        )


def default_icon_path() -> str:
    """Get the default path to battery icons"""
    dir_path = Path(__file__).resolve() / ".." / ".." / "resources" / "battery-icons"
    return str(dir_path.resolve())


class BatteryIcon(base._Widget):
    """Battery life indicator widget."""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("battery", 0, "Which battery should be monitored"),
        ("update_interval", 60, "Seconds between status updates"),
        ("theme_path", default_icon_path(), "Path of the icons"),
        ("scale", 1, "Scale factor relative to the bar height.  " "Defaults to 1"),
    ]  # type: list[tuple[str, Any, str]]

    icon_names = (
        "battery-missing",
        "battery-caution",
        "battery-low",
        "battery-good",
        "battery-full",
        "battery-caution-charging",
        "battery-low-charging",
        "battery-good-charging",
        "battery-full-charging",
        "battery-full-charged",
    )

    def __init__(self, **config) -> None:
        if "update_delay" in config:
            warnings.warn(
                "Change from using update_delay to update_interval for battery widget, removed in 0.15",
                DeprecationWarning,
            )
            config["update_interval"] = config.pop("update_delay")

        base._Widget.__init__(self, length=bar.CALCULATED, **config)
        self.add_defaults(self.defaults)
        self.scale = 1.0 / self.scale  # type: float

        self.length_type = bar.STATIC
        self.length = 0
        self.image_padding = 0
        self.surfaces = {}  # type: dict[str, Img]
        self.current_icon = "battery-missing"

        self._battery = self._load_battery(**config)

    @staticmethod
    def _load_battery(**config):
        """Function used to load the Battery object

        Battery behavior can be changed by overloading this function in a base
        class.
        """
        return load_battery(**config)

    def timer_setup(self) -> None:
        self.update()
        self.timeout_add(self.update_interval, self.timer_setup)

    def _configure(self, qtile, bar) -> None:
        base._Widget._configure(self, qtile, bar)
        self.image_padding = 0
        self.setup_images()
        self.image_padding = (self.bar.height - self.bar.height / 5) / 2

    def setup_images(self) -> None:
        d_imgs = images.Loader(self.theme_path)(*self.icon_names)

        new_height = self.bar.height * self.scale - self.image_padding
        for key, img in d_imgs.items():
            img.resize(height=new_height)
            if img.width > self.length:
                self.length = int(img.width + self.image_padding * 2)
            self.surfaces[key] = img.pattern

    def update(self) -> None:
        status = self._battery.update_status()
        icon = self._get_icon_key(status)
        if icon != self.current_icon:
            self.current_icon = icon
            self.draw()

    def draw(self) -> None:
        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.set_source(self.surfaces[self.current_icon])
        self.drawer.ctx.paint()
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    @staticmethod
    def _get_icon_key(status: BatteryStatus) -> str:
        key = "battery"

        percent = status.percent
        if percent < 0.2:
            key += "-caution"
        elif percent < 0.4:
            key += "-low"
        elif percent < 0.8:
            key += "-good"
        else:
            key += "-full"

        state = status.state
        if state == BatteryState.CHARGING:
            key += "-charging"
        elif state == BatteryState.FULL:
            key += "-charged"
        return key
