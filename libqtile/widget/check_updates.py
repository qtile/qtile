# Copyright (c) 2015 Ali Mousavi
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
from subprocess import CalledProcessError, Popen

from libqtile.log_utils import logger
from libqtile.widget import base


class CheckUpdates(base.ThreadedPollText):
    """Shows number of pending updates in different unix systems"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("distro", "Arch", "Name of your distribution"),
        ("custom_command", None, "Custom shell command for checking updates (counts the lines of the output)"),
        ("update_interval", 60, "Update interval in seconds."),
        ('execute', None, 'Command to execute on click'),
        ("display_format", "Updates: {updates}", "Display format if updates available"),
        ("colour_no_updates", "ffffff", "Colour when there's no updates."),
        ("colour_have_updates", "ffffff", "Colour when there are updates."),
        ("restart_indicator", "", "Indicator to represent reboot is required. (Ubuntu only)")
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(CheckUpdates.defaults)

        # format: "Distro": ("cmd", "number of lines to subtract from output")
        self.cmd_dict = {"Arch": ("pacman -Qu", 0),
                         "Arch_checkupdates": ("checkupdates", 0),
                         "Arch_Sup": ("pacman -Sup", 1),
                         "Arch_yay": ("yay -Qu", 0),
                         "Debian": ("apt-show-versions -u -b", 0),
                         "Ubuntu": ("aptitude search ~U", 0),
                         "Fedora": ("dnf list updates", 3),
                         "FreeBSD": ("pkg_version -I -l '<'", 0),
                         "Mandriva": ("urpmq --auto-select", 0)
                         }

        # Check if distro name is valid.
        try:
            self.cmd = self.cmd_dict[self.distro][0].split()
            self.subtr = self.cmd_dict[self.distro][1]
        except KeyError:
            distros = sorted(self.cmd_dict.keys())
            logger.error(self.distro + ' is not a valid distro name. ' +
                         'Use one of the list: ' + str(distros) + '.')
            self.cmd = None

    def _check_updates(self):
        # type: () -> str
        try:
            if self.custom_command is None:
                updates = self.call_process(self.cmd)
            else:
                updates = self.call_process(self.custom_command, shell=True)
                self.subtr = 0
        except CalledProcessError:
            updates = ""
        num_updates = str(len(updates.splitlines()) - self.subtr)

        if self.restart_indicator and os.path.exists('/var/run/reboot-required'):
            num_updates += self.restart_indicator

        self._set_colour(num_updates)
        return self.display_format.format(**{"updates": num_updates})

    def _set_colour(self, num_updates):
        # type: (str) -> None
        if not num_updates.startswith("0"):
            self.layout.colour = self.colour_have_updates
        else:
            self.layout.colour = self.colour_no_updates

    def poll(self):
        # type: () -> str
        if not self.cmd:
            return "N/A"
        return self._check_updates()

    def button_press(self, x, y, button):
        # type: (int, int, int) -> None
        base.ThreadedPollText.button_press(self, x, y, button)
        if button == 1 and self.execute is not None:
            Popen(self.execute, shell=True)
