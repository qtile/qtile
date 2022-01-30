# Copyright (c) 2013 Jacob Mourelos
# Copyright (c) 2014 Shepilov Vladislav
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2019 zordsdavini
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

import re
from abc import ABCMeta, abstractmethod
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING

from libqtile.confreader import ConfigError
from libqtile.log_utils import logger
from libqtile.widget import base

if TYPE_CHECKING:
    from libqtile.core.manager import Qtile


class _BaseLayoutBackend(metaclass=ABCMeta):
    def __init__(self, qtile: Qtile):
        """
        This handles getting and setter the keyboard layout with the appropriate
        backend.
        """

    @abstractmethod
    def get_keyboard(self) -> str:
        """
        Return the currently used keyboard layout as a string

        Examples: "us", "us dvorak".  In case of error returns "unknown".
        """

    def set_keyboard(self, layout: str, options: str | None) -> None:
        """
        Set the keyboard layout with specified options.
        """


class _X11LayoutBackend(_BaseLayoutBackend):
    kb_layout_regex = re.compile(r"layout:\s+(?P<layout>\w+)")
    kb_variant_regex = re.compile(r"variant:\s+(?P<variant>\w+)")

    def get_keyboard(self) -> str:
        try:
            command = "setxkbmap -verbose 10 -query"
            setxkbmap_output = check_output(command.split(" ")).decode()
        except CalledProcessError as e:
            logger.error("Can not get the keyboard layout: {0}".format(e))
            return "unknown"
        except OSError as e:
            logger.error("Please, check that xset is available: {0}".format(e))
            return "unknown"

        match_layout = self.kb_layout_regex.search(setxkbmap_output)
        if match_layout is None:
            return "ERR"
        keyboard = match_layout.group("layout")

        match_variant = self.kb_variant_regex.search(setxkbmap_output)
        if match_variant:
            keyboard += " " + match_variant.group("variant")
        return keyboard

    def set_keyboard(self, layout: str, options: str | None) -> None:
        command = ["setxkbmap"]
        command.extend(layout.split(" "))
        if options:
            command.extend(["-option", options])
        try:
            check_output(command)
        except CalledProcessError as e:
            logger.error("Can not change the keyboard layout: {0}".format(e))
        except OSError as e:
            logger.error("Please, check that setxkbmap is available: {0}".format(e))


class _WaylandLayoutBackend(_BaseLayoutBackend):
    def __init__(self, qtile: Qtile) -> None:
        self.set_keymap = qtile.core.cmd_set_keymap  # type: ignore
        self._layout: str = ""

    def get_keyboard(self) -> str:
        return self._layout

    def set_keyboard(self, layout: str, options: str | None) -> None:
        maybe_variant: str | None = None
        if " " in layout:
            layout_name, maybe_variant = layout.split(" ", maxsplit=1)
        else:
            layout_name = layout
        self.set_keymap(layout_name, options, maybe_variant)
        self._layout = layout


layout_backends = {
    "x11": _X11LayoutBackend,
    "wayland": _WaylandLayoutBackend,
}


class KeyboardLayout(base.InLoopPollText):
    """Widget for changing and displaying the current keyboard layout

    To use this widget effectively you need to specify keyboard layouts you want to use
    (using "configured_keyboards") and bind function "next_keyboard" to specific keys in
    order to change layouts.

    For example:

        Key([mod], "space", lazy.widget["keyboardlayout"].next_keyboard(), desc="Next keyboard layout."),

    When running Qtile with the X11 backend, this widget requires setxkbmap to be available.
    """

    defaults = [
        ("update_interval", 1, "Update time in seconds."),
        (
            "configured_keyboards",
            ["us"],
            "A list of predefined keyboard layouts "
            "represented as strings. For example: "
            "['us', 'us colemak', 'es', 'fr'].",
        ),
        (
            "display_map",
            {},
            "Custom display of layout. Key should be in format "
            "'layout variant'. For example: "
            "{'us': 'us', 'lt sgs': 'sgs', 'ru phonetic': 'ru'}",
        ),
        ("option", None, "string of setxkbmap option. Ex., 'compose:menu,grp_led:scroll'"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardLayout.defaults)
        self.add_callbacks({"Button1": self.next_keyboard})

    def _configure(self, qtile, bar):
        base.InLoopPollText._configure(self, qtile, bar)

        if qtile.core.name not in layout_backends:
            raise ConfigError("KeyboardLayout does not support backend: " + qtile.core.name)

        self.backend = layout_backends[qtile.core.name](qtile)
        self.backend.set_keyboard(self.configured_keyboards[0], self.option)

    def next_keyboard(self):
        """set the next layout in the list of configured keyboard layouts as
        new current layout in use

        If the current keyboard layout is not in the list, it will set as new
        layout the first one in the list.
        """

        current_keyboard = self.backend.get_keyboard()
        if current_keyboard in self.configured_keyboards:
            # iterate the list circularly
            next_keyboard = self.configured_keyboards[
                (self.configured_keyboards.index(current_keyboard) + 1)
                % len(self.configured_keyboards)
            ]
        else:
            next_keyboard = self.configured_keyboards[0]

        self.backend.set_keyboard(next_keyboard, self.option)

        self.tick()

    def poll(self):
        keyboard = self.backend.get_keyboard()
        if keyboard in self.display_map.keys():
            return self.display_map[keyboard]
        return keyboard.upper()

    def cmd_next_keyboard(self):
        """Select next keyboard layout"""
        self.next_keyboard()
