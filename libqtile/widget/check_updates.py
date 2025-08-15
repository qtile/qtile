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

# format: "Distro": ("cmd", "number of lines to subtract from output")
CMD_DICT = {
    "Arch": ("pacman -Qu", 0),
    "Arch_checkupdates": ("checkupdates", 0),
    "Arch_Sup": ("pacman -Sup", 0),
    "Arch_paru": ("paru -Qu", 0),
    "Arch_paru_Sup": ("paru -Sup", 0),
    "Arch_yay": ("yay -Qu", 0),
    "Debian": ("apt-show-versions -u -b", 0),
    "Gentoo_eix": ("EIX_LIMIT=0 eix -u# --world", 0),
    "Guix": ("guix upgrade --dry-run", 0),
    "Ubuntu": ("aptitude search ~U", 0),
    "Fedora": ("dnf list --upgrades -q", 1),
    "FreeBSD": ("pkg upgrade -n | awk '/\t/ { print $0 }'", 0),
    "Mandriva": ("urpmq --auto-select", 0),
    "Void": ("xbps-install -nuMS", 0),
}

# We need the spaces here to ensure the indentation is correct in the docstring
CMD_DOC_COMMANDS = "\n".join(f"    * ``'{k}'`` runs ``{v}``" for k, v in CMD_DICT.items())


class CheckUpdates(base.BackgroundPoll):
    # The docstring includes some dynamic content so we need to compile that content
    # first and then set the docstring to that content.
    _doc = f"""
    Shows number of pending updates in different unix systems.

    The following built-in options are available via the ``distro`` parameter:

{CMD_DOC_COMMANDS}

    .. note::

        It is common for package managers to return a non-zero code when there are no
        updates. As a result, the widget will treat *any* error as if there are no updates.
        If you are using a custom commmand/script, you should therefore ensure that it
        returns zero when it completes if you wish to see the output of your command.

        In addition, as no errors are recorded to the log, if the widget is showing no
        updates and you believe that to be incorrect, you should run the appropriate
        command in a terminal to view any error messages.

    """

    __doc__ = _doc

    defaults = [
        ("distro", "Arch", "Name of your distribution"),
        (
            "custom_command",
            None,
            "Custom shell command for checking updates (counts the lines of the output)",
        ),
        (
            "custom_command_modify",
            (lambda x: x),
            "Lambda function to modify line count from custom_command",
        ),
        (
            "initial_text",
            "",
            "Draw the widget immediately with an initial text, "
            "useful if it takes time to check system updates.",
        ),
        ("update_interval", 60, "Update interval in seconds."),
        ("execute", None, "Command to execute on click"),
        ("display_format", "Updates: {updates}", "Display format if updates available"),
        ("colour_no_updates", "ffffff", "Colour when there's no updates."),
        ("colour_have_updates", "ffffff", "Colour when there are updates."),
        ("restart_indicator", "", "Indicator to represent reboot is required. (Ubuntu only)"),
        ("no_update_string", "", "String to display if no updates available"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, config.pop("initial_text", ""), **config)
        self.add_defaults(CheckUpdates.defaults)

        # Helpful to have this as a variable as we can shorten it for testing
        self.execute_polling_interval = 1

        if self.custom_command:
            # Use custom_command
            self.cmd = self.custom_command

        else:
            # Check if distro name is valid.
            try:
                self.cmd = CMD_DICT[self.distro][0]
                self.custom_command_modify = lambda x: x - CMD_DICT[self.distro][1]
            except KeyError:
                distros = sorted(CMD_DICT.keys())
                logger.error(
                    "%s is not a valid distro name. Use one of the list: %s.",
                    self.distro,
                    str(distros),
                )
                self.cmd = None

        if self.execute:
            self.add_callbacks({"Button1": self.do_execute})

    def _check_updates(self):
        # type: () -> str
        try:
            updates = self.call_process(self.cmd, shell=True)
        except CalledProcessError:
            updates = ""
        num_updates = self.custom_command_modify(len(updates.splitlines()))

        if num_updates < 0:
            num_updates = 0
        if num_updates == 0:
            self.layout.colour = self.colour_no_updates
            return self.no_update_string
        num_updates = str(num_updates)

        if self.restart_indicator and os.path.exists("/var/run/reboot-required"):
            num_updates += self.restart_indicator

        self.layout.colour = self.colour_have_updates
        return self.display_format.format(updates=num_updates)

    def poll(self):
        # type: () -> str
        if not self.cmd:
            return "N/A"
        return self._check_updates()

    def do_execute(self):
        self._process = Popen(self.execute, shell=True)
        self.timeout_add(self.execute_polling_interval, self._refresh_count)

    def _refresh_count(self):
        if self._process.poll() is None:
            self.timeout_add(self.execute_polling_interval, self._refresh_count)

        else:
            self.timer_setup()
