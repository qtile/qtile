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
import os
import re
import platform
from abc import ABC, abstractclassmethod
from enum import Enum, auto, unique
from subprocess import check_output, CalledProcessError
from libqtile import bar
from libqtile.log_utils import logger
from . import base
from .. import images, configurable

from typing import Dict


@unique
class State(Enum):
    CHARGING = auto()
    DISCHARGING = auto()
    FULL = auto()
    EMPTY = auto()
    UNKNOWN = auto()


class _Battery(ABC):
    """
        Battery interface class specifying what member functions a
        battery implementation should provide.
    """
    @abstractclassmethod
    def _update_data(self):
        """
            Reads the battery status from the system and stores the
            result internally for later retrieval. Is called every
            time battery status is queried.

            No return

            Raises RuntimeError on error.
        """
        pass

    @abstractclassmethod
    def _get_state(self):
        """
            Returns the state of the battery.

            Return value is one of:
                State.CHARGING
                State.DISCHARGING
                State.FULL
                State.EMPTY
                State.UNKNOWN

            Raises RuntimeError on error.
        """
        pass

    @abstractclassmethod
    def _get_percentage(self):
        """
            Returns the percentage remaining in the battery in decimal
            form.

            Return value:
                float containing remaining charge percentage in
                decimal form

            Raises RuntimeError on error.
        """
        pass

    @abstractclassmethod
    def _get_power(self):
        """
            Returns the current power consumption in watts [W] as a
            number.

            Return value:
                float containing the current power consumption in
                watts [W].

            Raises RuntimeErorr on error.
        """
        pass

    @abstractclassmethod
    def _get_time(self):
        """
            Returns the estimated remaining battery time in seconds.

            Return value:
                int containing the seconds of battery time
                remaining.

            Raises RuntimeError on error.
        """
        pass


class _FreeBSDBattery(_Battery):
    """
        A battery class compatible with FreeBSD. Reads battery status
        using acpiconf.

        Takes a battery setting containing the number of the battery
        that should be monitored.
    """

    def __init__(self, battery='0'):
        self.battery = battery
        self._update_data()

    def _update_data(self):
        try:
            self.info = \
                check_output(['acpiconf', '-i', self.battery]).decode('utf-8')
        except CalledProcessError:
            raise RuntimeError('acpiconf exited incorrectly')

    def _get_state(self):
        stat = re.search(r'State:\t+([a-z]+)', self.info)

        if stat is None:
            raise RuntimeError('Could not get battery state!')

        stat = stat.group(1)
        if stat == 'charging':
            result = State.CHARGING
        elif stat == 'discharging':
            result = State.DISCHARGING
        elif stat == 'high':
            result = State.FULL
        else:
            result = State.UNKNOWN

        return result

    def _get_percentage(self):
        pct = re.search(r'Remaining capacity:\t+([0-9]+)', self.info)
        if pct:
            return int(pct.group(1)) / 100
        else:
            raise RuntimeError('Could not get battery percentage!')

    def _get_power(self):
        pow = re.search(r'Present rate:\t+(?:[0-9]+ mA )*\(?([0-9]+) mW',
                        self.info)
        if pow:
            return float(pow.group(1)) / 1000
        else:
            raise RuntimeError('Could not get battery power!')

    def _get_time(self):
        time = re.search(r'Remaining time:\t+([0-9]+:[0-9]+|unknown)',
                         self.info)
        if time:
            if time.group(1) == 'unknown':
                return 0
            else:
                time = time.group(1).split(':')
                return int(time[0]) * 3600 + int(time[1]) * 60
        else:
            raise RuntimeError('Could not get remaining battery time!')


class _LinuxBattery(_Battery, configurable.Configurable):
    defaults = [
        (
            'status_file',
            'status',
            'Name of status file in'
            ' /sys/class/power_supply/battery_name'
        ),
        (
            'energy_now_file',
            None,
            'Name of file with the '
            'current energy in /sys/class/power_supply/battery_name'
        ),
        (
            'energy_full_file',
            None,
            'Name of file with the maximum'
            ' energy in /sys/class/power_supply/battery_name'
        ),
        (
            'power_now_file',
            None,
            'Name of file with the current'
            ' power draw in /sys/class/power_supply/battery_name'
        )
    ]

    filenames: Dict = {}

    BAT_DIR = '/sys/class/power_supply'

    BATTERY_INFO_FILES = {
        'energy_now_file': ['energy_now', 'charge_now'],
        'energy_full_file': ['energy_full', 'charge_full'],
        'power_now_file': ['power_now', 'current_now'],
        'voltage_now_file': ['voltage_now'],
        'status_file': ['status'],
    }

    CHARGED = 'Full'
    CHARGING = 'Charging'
    DISCHARGING = 'Discharging'
    UNKNOWN = 'Unknown'

    stat = ''
    now = 0
    full = 0
    power = 0
    voltage = 0

    def _get_battery_name(self):
        if os.path.isdir(self.BAT_DIR):
            bats = [f for f in os.listdir(self.BAT_DIR) if f.startswith('BAT')]
            if bats:
                return bats[0]
        return 'BAT0'

    def __init__(self, **config):
        _LinuxBattery.defaults.append(('battery',
                                       self._get_battery_name(),
                                       'ACPI name of a battery, usually BAT0'))

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_LinuxBattery.defaults)

    def _load_file(self, name):
        try:
            path = os.path.join(self.BAT_DIR, self.battery, name)
            if 'energy'in name or 'power' in name:
                value_type = 'uW'
            elif 'charge' in name or 'current' in name:
                value_type = 'uA'
            elif 'voltage' in name:
                value_type = 'V'
            else:
                value_type = ''

            with open(path, 'r') as f:
                return (f.read().strip(), value_type,)
        except IOError:
            if name == 'current_now':
                return 0
            return False
        except Exception:
            logger.exception("Failed to get %s" % name)

    def _get_param(self, name):
        if name in self.filenames and self.filenames[name]:
            return self._load_file(self.filenames[name])
        elif name not in self.filenames:
            # Don't have the file name cached, figure it out

            # Don't modify the global list! Copy with [:]
            file_list = self.BATTERY_INFO_FILES.get(name, [])[:]

            if getattr(self, name, None):
                # If a file is manually specified, check it first
                file_list.insert(0, getattr(self, name))

            # Iterate over the possibilities, and return the first valid value
            for file in file_list:
                value = self._load_file(file)
                if value is not False and value is not None:
                    self.filenames[name] = file
                    return value

        # If we made it this far, we don't have a valid file.
        # Set it to None to avoid trying the next time.
        self.filenames[name] = None

        return None

    def _update_data(self):
        try:
            self.stat = self._get_param('status_file')[0]

            self.now = self._get_param('energy_now_file')
            self.now = (float(self.now[0]), self.now[1],)

            self.full = self._get_param('energy_full_file')
            self.full = (float(self.full[0]), self.full[1],)

            self.power = self._get_param('power_now_file')
            self.power = (float(self.power[0]), self.power[1],)

            self.voltage = self._get_param('voltage_now_file')
            self.voltage = (float(self.voltage[0]), self.voltage[1],)
        except TypeError:
            raise RuntimeError('Got unexpected data type when updating ' +
                               'LinuxBattery data.')

    def _get_state(self):
        state = State.UNKNOWN
        if self.stat == self.CHARGED:
            state = State.FULL
        elif self.stat == self.CHARGING:
            state = State.CHARGING
        elif self.stat == self.DISCHARGING:
            state = State.DISCHARGING

        return state

    def _get_percentage(self):
        return self.now[0] / self.full[0]

    def _get_power(self):
        power = 0
        if self.power[1] == 'uA':
            power = (self.voltage[0] * self.power[0]) / 1e12
        elif self.power[1] == 'uW':
            power = self.power[0] / 1e6
        return power

    def _get_time(self):
        if self.power[0] == 0:
            return 0

        time = 0
        state = self._get_state()

        # Multiply the uAh and uWh by 3600 to get results in seconds.
        now = self.now[0] * 3600
        full = self.full[0] * 3600
        power = self.power[0]

        if state == State.DISCHARGING:
            time = now / power
        elif state == State.CHARGING:
            time = (full - now) / power

        return int(time)


class Battery(base._TextBox):
    """A text-based battery monitoring widget currently supporting FreeBSD"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('charge_char', '^', 'Character to indicate the battery is charging'),
        ('discharge_char',
         'V',
         'Character to indicate the battery is discharging'
         ),
        ('full_char', '=', 'Character to indicate the battery is full'),
        ('empty_char', 'x', 'Character to indicate the battery is empty'),
        ('unknown_char',
         '?',
         'Character to indicate the battery status is unknown'),
        ('format',
         '{char} {percent:2.0%} {hour:d}:{min:02d} {watt:.2f} W',
         'Display format'
         ),
        ('hide_threshold',
         None,
         'Hide the text when there is enough energy 0 <= x < 1'),
        ('low_percentage',
         0.10,
         "Indicates when to use the low_foreground color 0 < x < 1"
         ),
        ('low_foreground', 'FF0000', 'Font color on low battery'),
        ('update_delay', 60, 'Seconds between status updates'),
        ('battery', 0, 'Which battery should be monitored'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "BAT", bar.CALCULATED, **config)
        self.add_defaults(self.defaults)

        system = platform.system()
        if system == 'FreeBSD':
            self.battery = _FreeBSDBattery(str(self.battery))
        elif system == 'Linux':
            self.battery = _LinuxBattery(**config)
        else:
            raise RuntimeError('Unknown platform!')

    def timer_setup(self):
        self.update()
        self.timeout_add(self.update_delay, self.timer_setup)

    def _configure(self, qtile, bar):
        if self.configured:
            self.update()

        base._TextBox._configure(self, qtile, bar)

    def _get_text(self):
        """
            Function returning a string with battery information to
            display on the status bar. Should only use the public
            interface in _Battery to get necessary information for
            constructing the string.

            If some information is missing, modify the interface to
            keep portability.
        """
        try:
            self.battery._update_data()

            state = self.battery._get_state()
            percent = self.battery._get_percentage()
            power = self.battery._get_power()
            time = self.battery._get_time()

            if self.hide_threshold is not None and \
                    percent > self.hide_threshold:
                return ''

            if state == State.DISCHARGING and percent < self.low_percentage:
                self.layout.colour = self.low_foreground
            else:
                self.layout.colour = self.foreground

            if state == State.CHARGING:
                char = self.charge_char
            elif state == State.DISCHARGING:
                char = self.discharge_char
            elif state == State.FULL:
                char = self.full_char
            elif state == State.EMPTY:
                char = self.empty_char
            elif state == State.UNKNOWN:
                char = self.unknown_char

            hour = time // 3600
            minute = (time // 60) % 60

            return self.format.format(
                char=char,
                percent=percent,
                watt=power,
                hour=hour,
                min=minute
            )
        except RuntimeError as e:
            return 'Error: {}'.format(str(e))

    def update(self):
        ntext = self._get_text()
        if ntext != self.text:
            self.text = ntext
            self.bar.draw()


class BatteryIcon(base._TextBox):
    """Battery life indicator widget."""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('battery', 0, 'Which battery should be monitored'),
        ('update_delay', 60, 'Seconds between status updates'),
    ]

    icon_names = (
        'battery-missing',
        'battery-caution',
        'battery-low',
        'battery-good',
        'battery-full',
        'battery-caution-charging',
        'battery-low-charging',
        'battery-good-charging',
        'battery-full-charging',
        'battery-full-charged',
    )

    def default_icon_path(self):
        # default icons are in libqtile/resources/battery-icons
        root = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
        return os.path.join(root, 'resources', 'battery-icons')

    def __init__(self, **config):
        base._TextBox.__init__(self, "BAT", bar.CALCULATED, **config)

        self.defaults.append(('theme_path', self.default_icon_path(),
                              'Path of the icons'))
        self.add_defaults(self.defaults)

        system = platform.system()
        if system == 'FreeBSD':
            self.battery = _FreeBSDBattery(str(self.battery))
        elif system == 'Linux':
            self.battery = _LinuxBattery(**config)
        else:
            raise RuntimeError('Unknown platform!')

        if self.theme_path:
            self.length_type = bar.STATIC
            self.length = 0
        self.surfaces = {}
        self.current_icon = 'battery-missing'

    def timer_setup(self):
        self.update()
        self.timeout_add(self.update_delay, self.timer_setup)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        if self.theme_path:
            self.setup_images()

    def _get_icon_key(self):
        key = 'battery'
        percent = self.battery._get_percentage()

        if percent < .2:
            key += '-caution'
        elif percent < .4:
            key += '-low'
        elif percent < .8:
            key += '-good'
        else:
            key += '-full'

        state = self.battery._get_state()
        if state == State.CHARGING:
            key += '-charging'
        elif state == State.FULL:
            key += '-charged'
        return key

    def update(self):
        self.battery._update_data()
        icon = self._get_icon_key()
        if icon != self.current_icon:
            self.current_icon = icon
            self.draw()

    def draw(self):
        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            self.drawer.ctx.set_source(self.surfaces[self.current_icon])
            self.drawer.ctx.paint()
            self.drawer.draw(offsetx=self.offset, width=self.length)
        else:
            self.text = self.current_icon[8:]
            base._TextBox.draw(self)

    def setup_images(self):
        d_imgs = images.Loader(self.theme_path)(*self.icon_names)
        new_height = self.bar.height - self.actual_padding
        surfs = self.surfaces
        for key, img in d_imgs.items():
            img.resize(height=new_height)
            if img.width > self.length:
                self.length = int(img.width + self.actual_padding * 2)
            surfs[key] = img.pattern
