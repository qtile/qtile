# Copyright (c) 2013 Jacob Mourelos
# Copyright (c) 2014 Shepilov Vladislav
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Tycho Andersen
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

from . import base
from libqtile.log_utils import logger


kb_layout_regex = re.compile(r'layout:\s+(?P<layout>\w+)')
kb_variant_regex = re.compile(r'variant:\s+(?P<variant>\w+)')


class KeyboardLayout(base.InLoopPollText):
    """Widget for changing and displaying the current keyboard layout

    It requires setxkbmap to be available in the system.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 1, "Update time in seconds."),
        ("configured_keyboards", ["us"], "A list of predefined keyboard layouts "
            "represented as strings. For example: "
            "['us', 'us colemak', 'es', 'fr']."),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardLayout.defaults)

    def button_press(self, x, y, button):
        if button == 1:
            self.next_keyboard()

    def next_keyboard(self):
        """Set the next layout in the list of configured keyboard layouts as
        new current layout in use

        If the current keyboard layout is not in the list, it will set as new
        layout the first one in the list.
        """

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
        return self.keyboard.upper()

    def get_keyboard_layout(self, setxkbmap_output):
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
        try:
            command = 'setxkbmap -verbose 10'
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
        command = ['setxkbmap']
        command.extend(keyboard.split(" "))
        try:
            self.call_process(command)
        except CalledProcessError as e:
            logger.error('Can not change the keyboard layout: {0}'.format(e))
        except OSError as e:
            logger.error('Please, check that setxkbmap is available: {0}'.format(e))

    def cmd_next_keyboard(self):
        """Select next keyboard layout"""
        self.next_keyboard()
