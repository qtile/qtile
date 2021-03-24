# Copyright (c) 2013 Jacob Mourelos
# Copyright (c) 2014 Shepilov Vladislav
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2019 zordsdavini
# Copyright (c) 2021 Mateja Maric
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

import re
from subprocess import CalledProcessError

from libqtile.log_utils import logger
from libqtile.widget import base

kb_layout_regex = re.compile(r'layout:\s+(?P<layout>\w+)')
kb_variant_regex = re.compile(r'variant:\s+(?P<variant>\w+)')


class KeyboardLayout(base.InLoopPollText):
    """Widget for changing and displaying the current keyboard layout.

    There are two ways of using this widget:

    **1. The First Way** (you need to have xkb-switch installed):

    If you set "use_xkb_switch" to True, this widget will act like most keyboard layout widgets in other WMs and status bars.
    You simply can simply set your keyboard layout (using "setxkbmap" for example) in your ".xinitrc" or "autostart.sh"
    and this widget will auto-detect and display your keyboard layout and update on changes.

    **2. The Second Way** (you need to have setxkbmap installed):

    You need to specify keyboard layouts you want to use (using "configured_keyboards")
    and bind function "next_keyboard" to specific keys in order to change layouts.

    For example:

        Key([mod], "space", lazy.widget["keyboardlayout"].next_keyboard(), desc="Next keyboard layout."),

    *Note that this way only layouts in "configured_keyboards" will be used.*

    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 0.2, "Update time in seconds."),
        ("use_xkb_switch", False, "You need xkb-switch installed. If True 'configured_keyboards' and 'option' variables won't be used."),
        ("configured_keyboards", ["us"], "A list of predefined keyboard layouts "
            "represented as strings. For example: "
            "['us', 'us colemak', 'es', 'fr']."),
        ("display_map", {}, "Custom display of layout. Key should be in format "
         "'layout variant':'display text'. For example: "
            "{'us': 'us ', 'lt sgs': 'sgs', 'ru phonetic': 'ru '}"),
        ("option", None, "String of setxkbmap option. Ex., 'compose:menu,grp_led:scroll'"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardLayout.defaults)

        if not self.use_xkb_switch:
            self.keyboard = self.configured_keyboards[0]

        self.add_callbacks({'Button1': self.next_keyboard})

    def next_keyboard(self):
        """Set the next layout in the list of configured keyboard layouts as
        new current layout in use

        If the current keyboard layout is not in the list, it will set as new
        layout the first one in the list.
        """
        if self.use_xkb_switch:
            try:
                self.call_process(['xkb-switch', '-n'])
            except CalledProcessError as e:
                logger.error("Can't set the keyboard layout (%s)", e)
        else:
            current_keyboard = self.keyboard
            if current_keyboard in self.configured_keyboards:
                # iterate the list circularly
                next_keyboard = self.configured_keyboards[
                    (self.configured_keyboards.index(current_keyboard) + 1) %
                    len(self.configured_keyboards)]
            else:
                next_keyboard = self.configured_keyboards[0]
            self.keyboard = next_keyboard

        self.tick()

    def poll(self):
        if self.keyboard in self.display_map.keys():
            return self.display_map[self.keyboard]
        return self.keyboard.upper()

    def get_keyboard_layout(self, setxkbmap_output):
        """Used by setxkbmap part of keyboard getter.

        Not called if xkb-switch is used.
        """
        match_layout = kb_layout_regex.search(setxkbmap_output)
        match_variant = kb_variant_regex.search(setxkbmap_output)

        if match_layout is None:
            return 'ERR'

        kb = match_layout.group('layout')
        if match_variant:
            kb += " " + match_variant.group('variant')
        return kb

    @property
    def keyboard(self):
        """Return the currently used keyboard layout as a string

        Examples: "us", "us dvorak".  In case of error returns "unknown".
        """
        if self.use_xkb_switch:
            try:
                return self.call_process(['xkb-switch', '-p']).replace('(', ' ').replace(')', ' ').rstrip()
            except CalledProcessError as e:
                logger.error('Can not get the keyboard layout: {0}'.format(e))
            except OSError as e:
                logger.error('Please, check that xkb-switch is available: {0}'.format(e))
        else:
            try:
                command = 'setxkbmap -verbose 10 -query'
                setxkbmap_output = self.call_process(command.split(' '))
                keyboard = self.get_keyboard_layout(setxkbmap_output)
                return str(keyboard)
            except CalledProcessError as e:
                logger.error('Can not get the keyboard layout: {0}'.format(e))
            except OSError as e:
                logger.error('Please, check that xset is available: {0}'.format(e))

        return "unknown"

    @keyboard.setter
    def keyboard(self, keyboard):
        """Not called if xkb-switch is used."""
        command = ['setxkbmap']
        command.extend(keyboard.split(" "))
        if self.option:
            command.extend(['-option', self.option])
        try:
            self.call_process(command)
        except CalledProcessError as e:
            logger.error('Can not change the keyboard layout: {0}'.format(e))
        except OSError as e:
            logger.error('Please, check that setxkbmap is available: {0}'.format(e))

    def cmd_next_keyboard(self):
        """Select next keyboard layout"""
        self.next_keyboard()
