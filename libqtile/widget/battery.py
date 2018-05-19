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

from __future__ import division

import cairocffi
import os
from libqtile import bar
from libqtile.log_utils import logger
from . import base

try:
    from typing import Dict  # noqa: F401
except ImportError:
    pass

BAT_DIR = '/sys/class/power_supply'
CHARGED = 'Full'
CHARGING = 'Charging'
DISCHARGING = 'Discharging'
UNKNOWN = 'Unknown'

BATTERY_INFO_FILES = {
    'energy_now_file': ['energy_now', 'charge_now'],
    'energy_full_file': ['energy_full', 'charge_full'],
    'power_now_file': ['power_now', 'current_now'],
    'status_file': ['status'],
}


def default_icon_path():
    # default icons are in libqtile/resources/battery-icons
    root = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
    return os.path.join(root, 'resources', 'battery-icons')


def _get_battery_name():
    if os.path.isdir(BAT_DIR):
        bats = [f for f in os.listdir(BAT_DIR) if f.startswith('BAT')]
        if bats:
            return bats[0]
    return 'BAT0'


class _Battery(base._TextBox):
    """Base battery class"""

    filenames = {}  # type: Dict

    defaults = [
        ('battery_name', _get_battery_name(), 'ACPI name of a battery, usually BAT0'),
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
        ),
        ('update_delay', 60, 'The delay in seconds between updates'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "BAT", bar.CALCULATED, **config)
        self.add_defaults(_Battery.defaults)

    def _load_file(self, name):
        try:
            path = os.path.join(BAT_DIR, self.battery_name, name)
            with open(path, 'r') as f:
                return f.read().strip()
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
            file_list = BATTERY_INFO_FILES.get(name, [])[:]

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

    def _get_info(self):
        try:
            info = {
                'stat': self._get_param('status_file'),
                'now': float(self._get_param('energy_now_file')),
                'full': float(self._get_param('energy_full_file')),
                'power': float(self._get_param('power_now_file')),
            }
        except TypeError:
            return False
        return info


class Battery(_Battery):
    """A simple but flexible text-based battery widget"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('charge_char', '^', 'Character to indicate the battery is charging'),
        ('discharge_char',
         'V',
         'Character to indicate the battery is discharging'
         ),
        ('error_message', 'Error', 'Error message if something is wrong'),
        ('format',
         '{char} {percent:2.0%} {hour:d}:{min:02d}',
         'Display format'
         ),
        ('hide_threshold', None, 'Hide the text when there is enough energy'),
        ('low_percentage',
         0.10,
         "Indicates when to use the low_foreground color 0 < x < 1"
         ),
        ('low_foreground', 'FF0000', 'Font color on low battery'),
    ]

    def __init__(self, **config):
        _Battery.__init__(self, **config)
        self.add_defaults(Battery.defaults)

    def timer_setup(self):
        update_delay = self.update()
        if update_delay is None and self.update_delay is not None:
            self.timeout_add(self.update_delay, self.timer_setup)
        elif update_delay:
            self.timeout_add(update_delay, self.timer_setup)

    def _configure(self, qtile, bar):
        if self.configured:
            self.update()
        _Battery._configure(self, qtile, bar)

    def _get_text(self):
        info = self._get_info()
        if info is False:
            return self.error_message

        # Set the charging character
        try:
            # hide the text when it's higher than threshold, but still
            # display `full` when the battery is fully charged.
            if self.hide_threshold and \
                    info['now'] / info['full'] * 100.0 >= \
                    self.hide_threshold and \
                    info['stat'] != CHARGED:
                return ''
            elif info['stat'] == DISCHARGING:
                char = self.discharge_char
                time = info['now'] / info['power']
            elif info['stat'] == CHARGING:
                char = self.charge_char
                time = (info['full'] - info['now']) / info['power']
            # if percent charge >0 and <50, but not discharging or charging, then return the current status
            # TODO: make this configurable, don't just use 50% as arbitrary cut-off, maybe check if plugged in
            elif info['now'] > 0 and \
                    info['stat'] == UNKNOWN and \
                    int(info['now'] / info['full']) != 1:
                return '~' + str(int(info['now'] / info['full'] * 100)) + '%'
            # battery is empty and not charging
            elif info['now'] == 0 and info['stat'] == UNKNOWN:
                return 'Empty'
            else:
                return 'Full'
        except ZeroDivisionError:
            time = -1

        # Calculate the battery percentage and time left
        if time >= 0:
            hour = int(time)
            min = int(time * 60) % 60
        else:
            hour = -1
            min = -1
        percent = info['now'] / info['full']
        watt = info['power'] / 1e6
        if info['stat'] == DISCHARGING and percent < self.low_percentage:
            self.layout.colour = self.low_foreground
        else:
            self.layout.colour = self.foreground

        return self.format.format(
            char=char,
            percent=percent,
            watt=watt,
            hour=hour,
            min=min
        )

    def update(self):
        ntext = self._get_text()
        if ntext != self.text:
            self.text = ntext
            self.bar.draw()


class BatteryIcon(_Battery):
    """Battery life indicator widget."""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('theme_path', default_icon_path(), 'Path of the icons'),
        ('custom_icons', {}, 'dict containing key->filename icon map'),
    ]

    def __init__(self, **config):
        _Battery.__init__(self, **config)
        self.add_defaults(BatteryIcon.defaults)

        if self.theme_path:
            self.length_type = bar.STATIC
            self.length = 0
        self.surfaces = {}
        self.current_icon = 'battery-missing'
        self.icons = dict([(x, '{0}.png'.format(x)) for x in (
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
        )])
        self.icons.update(self.custom_icons)

    def timer_setup(self):
        self.update()
        self.timeout_add(self.update_delay, self.timer_setup)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.setup_images()

    def _get_icon_key(self):
        key = 'battery'
        info = self._get_info()
        if info is False or not info.get('full'):
            key += '-missing'
        else:
            percent = info['now'] / info['full']
            if percent < .2:
                key += '-caution'
            elif percent < .4:
                key += '-low'
            elif percent < .8:
                key += '-good'
            else:
                key += '-full'

            if info['stat'] == CHARGING:
                key += '-charging'
            elif info['stat'] == CHARGED:
                key += '-charged'
        return key

    def update(self):
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
        for key, name in self.icons.items():
            try:
                path = os.path.join(self.theme_path, name)
                img = cairocffi.ImageSurface.create_from_png(path)
            except cairocffi.Error:
                self.theme_path = None
                logger.warning('Battery Icon switching to text mode')
                return
            input_width = img.get_width()
            input_height = img.get_height()

            sp = input_height / (self.bar.height - 1)

            width = input_width / sp
            if width > self.length:
                # cast to `int` only after handling all potentially-float values
                self.length = int(width + self.actual_padding * 2)

            imgpat = cairocffi.SurfacePattern(img)

            scaler = cairocffi.Matrix()

            scaler.scale(sp, sp)
            scaler.translate(self.actual_padding * -1, 0)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairocffi.FILTER_BEST)
            self.surfaces[key] = imgpat
