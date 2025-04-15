# Copyright (c) 2012 Tim Neumann
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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

import enum
import os
import shlex
from functools import partial

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

BACKLIGHT_DIR = "/sys/class/backlight"


@enum.unique
class ChangeDirection(enum.Enum):
    UP = 0
    DOWN = 1


class Backlight(base.InLoopPollText):
    """A simple widget to show the current brightness of a monitor.

    If the change_command parameter is set to None, the widget will attempt to
    use the interface at /sys/class to change brightness. This depends on
    having the correct udev rules, so be sure Qtile's udev rules are installed
    correctly.

    You can also bind keyboard shortcuts to the backlight widget with:

    .. code-block:: python

        from libqtile.widget import backlight
        Key(
            [],
            "XF86MonBrightnessUp",
            lazy.widget['backlight'].change_backlight(backlight.ChangeDirection.UP)
        )
        Key(
            [],
            "XF86MonBrightnessDown",
            lazy.widget['backlight'].change_backlight(backlight.ChangeDirection.DOWN)
        )
    """

    filenames: dict = {}

    defaults = [
        ("backlight_name", "acpi_video0", "ACPI name of a backlight device"),
        (
            "brightness_file",
            "brightness",
            "Name of file with the current brightness in /sys/class/backlight/backlight_name",
        ),
        (
            "max_brightness_file",
            "max_brightness",
            "Name of file with the maximum brightness in /sys/class/backlight/backlight_name",
        ),
        ("update_interval", 0.2, "The delay in seconds between updates"),
        ("step", 10, "Percent of backlight every scroll changed"),
        ("format", "{percent:2.0%}", "Display format"),
        ("change_command", "xbacklight -set {0}", "Execute command to change value"),
        ("min_brightness", 0, "Minimum brightness percentage"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Backlight.defaults)
        self._future = None

        self.brightness_file = os.path.join(
            BACKLIGHT_DIR,
            self.backlight_name,
            self.brightness_file,
        )
        self.max_brightness_file = os.path.join(
            BACKLIGHT_DIR,
            self.backlight_name,
            self.max_brightness_file,
        )

        self.add_callbacks(
            {
                "Button4": partial(self.change_backlight, ChangeDirection.UP),
                "Button5": partial(self.change_backlight, ChangeDirection.DOWN),
            }
        )

    def finalize(self):
        if self._future and not self._future.done():
            self._future.cancel()
        base.InLoopPollText.finalize(self)

    def _load_file(self, path):
        try:
            with open(path) as f:
                return float(f.read().strip())
        except FileNotFoundError:
            logger.debug("Failed to get %s", path)
            raise RuntimeError(f"Unable to read status for {os.path.basename(path)}")

    def _get_info(self):
        brightness = self._load_file(self.brightness_file)
        max_value = self._load_file(self.max_brightness_file)
        return brightness / max_value

    def poll(self):
        try:
            percent = self._get_info()
        except RuntimeError as e:
            return f"Error: {e}"

        return self.format.format(percent=percent)

    def _change_backlight(self, value):
        if self.change_command is None:
            value = self._load_file(self.max_brightness_file) * value / 100
            try:
                with open(self.brightness_file, "w") as f:
                    f.write(str(round(value)))
            except PermissionError:
                logger.warning(
                    "Cannot set brightness: no write permission for %s", self.brightness_file
                )
        else:
            self.call_process(shlex.split(self.change_command.format(value)))

    @expose_command()
    def change_backlight(self, direction, step=None):
        if not step:
            step = self.step
        if self._future and not self._future.done():
            return
        new = now = self._get_info() * 100
        if direction is ChangeDirection.DOWN:
            new = max(now - step, self.min_brightness)
        elif direction is ChangeDirection.UP:
            new = min(now + step, 100)
        if new != now:
            self._future = self.qtile.run_in_executor(self._change_backlight, new)
