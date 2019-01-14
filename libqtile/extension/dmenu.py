# Copyright (C) 2016, zordsdavini
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

import shlex
from . import base


class Dmenu(base.RunCommand):
    """
    Python wrapper for dmenu
    http://tools.suckless.org/dmenu/
    """

    defaults = [
        ("dmenu_font", None, "override the default 'font' and 'fontsize' options for dmenu"),
        # NOTE: Do not use a list as a default value, since it would be shared
        #       among all the objects inheriting this class, and if one of them
        #       modified it, all the other objects would see the modified list;
        #       use a string or a tuple instead, which are immutable
        ("dmenu_command", 'dmenu', "the dmenu command to be launched"),
        ("dmenu_bottom", False, "dmenu appears at the bottom of the screen"),
        ("dmenu_ignorecase", False, "dmenu matches menu items case insensitively"),
        ("dmenu_lines", None, "dmenu lists items vertically, with the given number of lines"),
        ("dmenu_prompt", None, "defines the prompt to be displayed to the left of the input field"),
        ("dmenu_height", None, "defines the height (only supported by some dmenu forks)"),
    ]

    def __init__(self, **config):
        base.RunCommand.__init__(self, **config)
        self.add_defaults(Dmenu.defaults)

    def _configure(self, qtile):
        base.RunCommand._configure(self, qtile)

        dmenu_command = self.dmenu_command or self.command
        if isinstance(dmenu_command, str):
            self.configured_command = shlex.split(dmenu_command)
        else:
            # Create a clone of dmenu_command, don't use it directly since
            # it's shared among all the instances of this class
            self.configured_command = list(dmenu_command)

        if self.dmenu_bottom:
            self.configured_command.append("-b")
        if self.dmenu_ignorecase:
            self.configured_command.append("-i")
        if self.dmenu_lines:
            self.configured_command.extend(("-l", str(self.dmenu_lines)))
        if self.dmenu_prompt:
            self.configured_command.extend(("-p", self.dmenu_prompt))

        if self.dmenu_font:
            font = self.dmenu_font
        elif self.font:
            if self.fontsize:
                font = '{}-{}'.format(self.font, self.fontsize)
            else:
                font = self.font
        self.configured_command.extend(("-fn", font))

        if self.background:
            self.configured_command.extend(("-nb", self.background))
        if self.foreground:
            self.configured_command.extend(("-nf", self.foreground))
        if self.selected_background:
            self.configured_command.extend(("-sb", self.selected_background))
        if self.selected_foreground:
            self.configured_command.extend(("-sf", self.selected_foreground))
        # NOTE: The original dmenu doesn't support the '-h' option
        if self.dmenu_height:
            self.configured_command.extend(("-h", str(self.dmenu_height)))

    def run(self, items=None):
        if items:
            if self.dmenu_lines:
                lines = min(len(items), self.dmenu_lines)
            else:
                lines = len(items)
            self.configured_command.extend(("-l", str(lines)))

        proc = super().run()

        if items:
            input_str = "\n".join([i for i in items]) + "\n"
            return proc.communicate(str.encode(input_str))[0].decode('utf-8')

        return proc


class DmenuRun(Dmenu):
    """
    Special case to run applications.

    config.py should have something like:

    .. code-block:: python

        from libqtile import extension
        keys = [
            Key(['mod4'], 'r', lazy.run_extension(extension.DmenuRun(
                dmenu_prompt=">",
                dmenu_font="Andika-8",
                background="#15181a",
                foreground="#00ff00",
                selected_background="#079822",
                selected_foreground="#fff",
                dmenu_height=24,  # Only supported by some dmenu forks
            ))),
        ]

    """

    defaults = [
        ("dmenu_command", 'dmenu_run', "the dmenu command to be launched"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(DmenuRun.defaults)

    def _configure(self, qtile):
        Dmenu._configure(self, qtile)


class J4DmenuDesktop(Dmenu):
    """
    Python wrapper for j4-dmenu-desktop
    https://github.com/enkore/j4-dmenu-desktop
    """

    defaults = [
        ("j4dmenu_command", 'j4-dmenu-desktop', "the dmenu command to be launched"),
        ("j4dmenu_use_xdg_de", False, "read $XDG_CURRENT_DESKTOP to determine the desktop environment"),
        ("j4dmenu_display_binary", False, "display binary name after each entry"),
        ("j4dmenu_generic", True, "include the generic name of desktop entries"),
        ("j4dmenu_terminal", None, "terminal emulator used to start terminal apps"),
        ("j4dmenu_usage_log", None, "file used to sort items by usage frequency"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(J4DmenuDesktop.defaults)

    def _configure(self, qtile):
        Dmenu._configure(self, qtile)

        self.configured_command = [self.j4dmenu_command, '--dmenu',
                                   " ".join(shlex.quote(arg) for arg in self.configured_command)]
        if self.j4dmenu_use_xdg_de:
            self.configured_command.append("--use-xdg-de")
        if self.j4dmenu_display_binary:
            self.configured_command.append("--display-binary")
        if not self.j4dmenu_generic:
            self.configured_command.append("--no-generic")
        if self.j4dmenu_terminal:
            self.configured_command.extend(("--term", self.j4dmenu_terminal))
        if self.j4dmenu_usage_log:
            self.configured_command.extend(("--usage-log",
                                            self.j4dmenu_usage_log))
