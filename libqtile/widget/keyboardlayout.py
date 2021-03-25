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

import re
from subprocess import CalledProcessError

from libqtile import qtile
from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.keyboard_helper import (
    connect_to_display,
    get_configured_layouts,
    get_group_index,
    set_group_index,
    set_listen_to_events,
)

kb_layout_regex = re.compile(r'layout:\s+(?P<layout>\w+)')
kb_variant_regex = re.compile(r'variant:\s+(?P<variant>\w+)')


class KeyboardLayout(base.InLoopPollText):
    """Widget for changing and displaying the current keyboard layout

    To use this widget effectively you need to specify keyboard layouts you want to use (using "configured_keyboards")
    and bind function "next_keyboard" to specific keys in order to change layouts.

    For example:

        Key([mod], "space", lazy.widget["keyboardlayout"].next_keyboard(), desc="Next keyboard layout."),

    It requires setxkbmap to be available in the system.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 1, "Update time in seconds."),
        ("configured_keyboards", ["us"], "A list of predefined keyboard layouts "
            "represented as strings. For example: "
            "['us', 'us colemak', 'es', 'fr']."),
        ("display_map", {}, "Custom display of layout. Key should be in format "
            "'layout variant'. For example: "
            "{'us': 'us ', 'lt sgs': 'sgs', 'ru phonetic': 'ru '}"),
        ("option", None, "string of setxkbmap option. Ex., 'compose:menu,grp_led:scroll'"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardLayout.defaults)
        connect_to_display(qtile.core.display_name.encode())
        set_listen_to_events()  # TODO: has no effect

        self.keyboard = self.configured_keyboards[0]

        self.add_callbacks({'Button1': self.next_keyboard})

    @staticmethod
    def num_configured_keyboards() -> int:
        """Return the number of configured layouts.

        This is equivalent to "count the ',' in `setxkbmap -query` and add 1".
        """
        # This defines how we actually work:
        # Some users prefer `setxkbmap layout1`, later `setxkbmap layout2`.
        # Others prefers `setxkbmap layout1,layout2` once and then to toggle dynamically.
        # If this returns 1, we do setxkbmap, otherwise we use set_group_index.
        # See `use_groups` below.
        return len(get_configured_layouts())

    @property
    def use_groups(self) -> bool:
        return self.num_configured_keyboards() > 1

    def next_keyboard(self):
        """Set the next layout in the list of configured keyboard layouts as
        new current layout in use

        If the current keyboard layout is not in the list, it will set as new
        layout the first one in the list.
        """

        current_keyboard = self.keyboard
        if self.use_groups:
            layouts = ['%s %s' % x if x.variant else x.layout for x in get_configured_layouts()]
            next_keyboard = layouts[(layouts.index(current_keyboard) + 1) % len(layouts)]
        else:
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
        if self.use_groups:
            layout = get_configured_layouts()[get_group_index()]
            return '%s %s' % layout if layout.variant else layout.layout
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
        if self.use_groups:
            kbspec = tuple(keyboard.split(' ')) if ' ' in keyboard else (keyboard, '')
            layouts = get_configured_layouts()
            if kbspec in layouts:
                set_group_index(layouts.index(kbspec))
            else:
                logger.error('Unable to set keyboard: %r is not in %r', kbspec, layouts)
            return
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
