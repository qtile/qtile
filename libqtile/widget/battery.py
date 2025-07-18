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
from abc import ABC, abstractmethod
from enum import Enum, unique
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING, NamedTuple

from libqtile import bar, configurable, images
from libqtile.command.base import expose_command
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
    NOT_CHARGING = 5
    UNKNOWN = 6


class BatteryStatus(NamedTuple):
    state: BatteryState
    percent: float
    power: float
    time: int
    charge_start_threshold: int
    charge_end_threshold: int


class _Battery(ABC):
    """
    Battery interface class specifying what member functions a
    battery implementation should provide.
    """

    @abstractmethod
    def update_status(self) -> BatteryStatus:
        """Read the battery status

        Reads the battery status from the system and returns the result.

        Raises RuntimeError on error.
        """


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
        return _FreeBSDBattery(str(config.get("battery", 0)))
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

        return BatteryStatus(
            state,
            percent=percent,
            power=power,
            time=time,
            charge_start_threshold=0,
            charge_end_threshold=100,
        )


def connected_to_thunderbolt():
    try:
        sysfs = "/sys/bus/thunderbolt/devices"
        entries = os.listdir(sysfs)
        for e in entries:
            try:
                name = Path(sysfs, e, "device_name").read_text()
            except FileNotFoundError:
                continue
            else:
                logger.debug("found dock %s", name)
                return True
    except OSError:
        logger.debug("failed to detect thunderbot %s", exc_info=True)
    return False


def thunderbolt_smart_charge() -> tuple[int, int]:
    # if we are thunderbolt docked, set the thresholds to 40/50, per
    # https://support.lenovo.com/us/en/solutions/ht078208-how-can-i-increase-battery-life-thinkpad-and-lenovo-vbke-series-notebooks
    if connected_to_thunderbolt():
        return (40, 50)
    return (0, 90)


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
        (
            "charge_controller",
            None,
            """
            A function that takes no arguments and returns (start, end) charge
            thresholds, e.g. ``lambda: (0, 90)``; set to None to disable smart
            charging.
            """,
        ),
        (
            "force_charge",
            False,
            "Whether or not to ignore the result of charge_controller() and charge to 100%",
        ),
    ]

    filenames: dict = {}

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
            self.battery = f"BAT{self.battery}"
        self.charge_threshold_supported = True

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
            with open(path) as f:
                return f.read().strip(), value_type
        except OSError as e:
            logger.debug("Failed to read '%s':", path, exc_info=True)
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

        raise RuntimeError(f"Unable to read status for {name}")

    def set_battery_charge_thresholds(self, start, end):
        if not self.charge_threshold_supported:
            return

        battery_dir = "/sys/class/power_supply"

        path = os.path.join(battery_dir, self.battery, "charge_control_start_threshold")
        try:
            with open(path, "w+") as f:
                f.write(str(start))
        except FileNotFoundError:
            self.charge_threshold_supported = False
        except OSError:
            logger.debug("Failed to write %s", path, exc_info=True)

        path = os.path.join(battery_dir, self.battery, "charge_control_end_threshold")
        try:
            with open(path, "w+") as f:
                f.write(str(end))
        except FileNotFoundError:
            self.charge_threshold_supported = False
        except OSError:
            logger.debug("Failed to write %s", path, exc_info=True)
        return (start, end)

    def update_status(self) -> BatteryStatus:
        charge_start_threshold = 0
        charge_end_threshold = 100
        if self.charge_controller is not None and self.charge_threshold_supported:
            (charge_start_threshold, charge_end_threshold) = self.charge_controller()
            if self.force_charge:
                charge_start_threshold = 0
                charge_end_threshold = 100
            self.set_battery_charge_thresholds(charge_start_threshold, charge_end_threshold)
        stat = self._get_param("status_file")[0]

        if stat == "Full":
            state = BatteryState.FULL
        elif stat == "Charging":
            state = BatteryState.CHARGING
        elif stat == "Discharging":
            state = BatteryState.DISCHARGING
        elif stat == "Not charging":
            state = BatteryState.NOT_CHARGING
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

        return BatteryStatus(
            state=state,
            percent=percent,
            power=power,
            time=time,
            charge_start_threshold=charge_start_threshold,
            charge_end_threshold=charge_end_threshold,
        )


class Battery(base.ThreadPoolText):
    """
    A text-based battery monitoring widget supporting both Linux and FreeBSD.

    The Linux version of this widget has functionality to charge "smartly"
    (i.e. not to 100%) under user defined conditions, and provides some
    implementations for doing so. For example, to only charge the battery to
    90%, use:

    .. code-block:: python

        Battery(..., charge_controller=lambda: (0, 90))

    The battery widget also supplies some charging algorithms. To only charge
    the battery between 40-50% while connected to a thunderbolt docking
    station, but 90% all other times, use:

    .. code-block:: python

        from libqtile.widget.battery import thunderbolt_smart_charge
        Battery(..., charge_controller=thunderbolt_smart_charge)

    To temporarily disable/re-enable this (e.g. if you know you're
    going mobile and need to charge) use either:

    .. code-block:: bash

        qtile cmd-obj -o bar top widget battery -f charge_to_full
        qtile cmd-obj -o bar top widget battery -f charge_dynamically

    or bind a key to:

    .. code-block:: python

        Key([mod, "shift"], "c", lazy.widget['battery'].charge_to_full())
        Key([mod, "shift"], "x", lazy.widget['battery'].charge_dynamically())

    note that this functionality requires qtile to be able to write to certain
    files in sysfs, so make sure that qtile's udev rules are installed
    correctly.
    """

    background: ColorsType | None
    low_background: ColorsType | None

    defaults = [
        ("charge_char", "^", "Character to indicate the battery is charging"),
        ("discharge_char", "V", "Character to indicate the battery is discharging"),
        ("full_char", "=", "Character to indicate the battery is full"),
        ("empty_char", "x", "Character to indicate the battery is empty"),
        ("not_charging_char", "*", "Character to indicate the batter is not charging"),
        ("unknown_char", "?", "Character to indicate the battery status is unknown"),
        ("format", "{char} {percent:2.0%} {hour:d}:{min:02d} {watt:.2f} W", "Display format"),
        ("hide_threshold", None, "Hide the text when there is enough energy 0 <= x < 1"),
        (
            "full_short_text",
            "Full",
            "Short text to indicate battery is full; see `show_short_text`",
        ),
        (
            "empty_short_text",
            "Empty",
            "Short text to indicate battery is empty; see `show_short_text`",
        ),
        (
            "show_short_text",
            True,
            "Show only characters rather than formatted text when battery is full or empty",
        ),
        ("low_percentage", 0.10, "Indicates when to use the low_foreground color 0 < x < 1"),
        ("low_foreground", "FF0000", "Font color on low battery"),
        ("low_background", None, "Background color on low battery"),
        (
            "charging_foreground",
            None,
            "Font color on charging battery. Set to None to disable.",
        ),
        (
            "charging_background",
            None,
            "Background color on charging battery. Set to None to disable.",
        ),
        ("update_interval", 60, "Seconds between status updates"),
        ("battery", 0, "Which battery should be monitored (battery number or name)"),
        ("notify_below", None, "Send a notification below this battery level."),
        ("notification_timeout", 10, "Time in seconds to display notification. 0 for no expiry."),
    ]

    def __init__(self, **config) -> None:
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

    @expose_command()
    def charge_to_full(self):
        self._battery.force_charge = True

    @expose_command()
    def charge_dynamically(self):
        self._battery.force_charge = False

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
            return f"Error: {e}"

        if self.notify_below:
            percent = int(status.percent * 100)
            if percent < self.notify_below:
                if not self._has_notified:
                    send_notification(
                        "Warning",
                        f"Battery at {status.percent:2.0%}",
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
            elif status.state == BatteryState.CHARGING:
                self.layout.colour = self.charging_foreground or self.foreground
                self.background = self.charging_background or self.normal_background
            else:
                self.layout.colour = self.foreground
                self.background = self.normal_background

        if status.state == BatteryState.CHARGING:
            char = self.charge_char
        elif status.state == BatteryState.DISCHARGING:
            char = self.discharge_char
        elif status.state == BatteryState.FULL:
            if self.show_short_text:
                return self.full_short_text
            char = self.full_char
        elif status.state == BatteryState.EMPTY or (
            status.state == BatteryState.UNKNOWN and status.percent == 0
        ):
            if self.show_short_text:
                return self.empty_short_text
            char = self.empty_char
        elif status.state == BatteryState.NOT_CHARGING:
            char = self.not_charging_char
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
    defaults: list[tuple[str, Any, str]] = [
        ("battery", 0, "Which battery should be monitored"),
        ("update_interval", 60, "Seconds between status updates"),
        ("theme_path", default_icon_path(), "Path of the icons"),
        ("scale", 1, "Scale factor relative to the bar height.  Defaults to 1"),
        ("padding", 0, "Additional padding either side of the icon"),
    ]

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
        base._Widget.__init__(self, length=bar.CALCULATED, **config)
        self.add_defaults(self.defaults)
        self.scale: float = 1.0 / self.scale

        self.image_padding = 0
        self.images: dict[str, Img] = {}
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
        self.setup_images()

    def setup_images(self) -> None:
        d_imgs = images.Loader(self.theme_path)(*self.icon_names)

        new_height = (self.bar.size - 2) * self.scale
        for key, img in d_imgs.items():
            img.resize(height=new_height)
            self.images[key] = img

    def calculate_length(self):
        if not self.images:
            return 0

        icon = self.images[self.current_icon]
        return icon.width + 2 * self.padding

    def update(self) -> None:
        status = self._battery.update_status()
        icon = self._get_icon_key(status)
        if icon != self.current_icon:
            self.current_icon = icon
            self.draw()

    def draw(self) -> None:
        self.drawer.clear(self.background or self.bar.background)
        image = self.images[self.current_icon]
        self.drawer.ctx.save()
        self.drawer.ctx.translate(self.padding, (self.bar.size - image.height) // 2)
        self.drawer.ctx.set_source(image.pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()
        self.draw_at_default_position()

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
