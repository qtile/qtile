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

import asyncio
from subprocess import CalledProcessError
from typing import NoReturn, Union

from libqtile.log_utils import logger
from libqtile.widget import base


class NoDependencyFoundError(Exception):
    pass


class KeyboardLayout(base.InLoopPollText):
    """
    Widget for changing and displaying the current keyboard layout group

    It requires xkb-switch to be available in the system.  setxkbmap is
    optional dependency (to configure the keyboard locally).
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            'compact',
            None,
            "Specifies the name of the compatibility map component used"
            " to construct a keyboard layout.",
        ),
        (
            'config_file',
            None,
            "Specifies the name of an XKB configuration file which"
            " describes the keyboard to be used.",
        ),
        (
            'device',
            None,
            "Specifies the numeric device id of the input device to be"
            " updated with the new keyboard layout. If not specified,"
            " the core keyboard device of the X server is updated.",
        ),
        (
            'display',
            None,
            "Specifies the display to be updated with the new keyboard"
            " layout.",
        ),
        (
            'geometry',
            None,
            "Specifies the name of the geometry component used to"
            " construct a keyboard layout.",
        ),
        (
            'dirs',
            None,
            "Adds a directory to the list of directories to be used to"
            " search for specified layout or rules files.",
        ),
        (
            'keycodes',
            None,
            "Specifies the name of the keycodes component used to"
            " construct a keyboard layout.",
        ),
        (
            'keymap',
            None,
            "Specifies the name of the keymap description used to"
            " construct a keyboard layout.",
        ),
        (
            'layout_groups',
            None,
            "Specifies the name of the layout used to determine the"
            " components which make up the keyboard description. For"
            " example: ['us', 'ru', 'sk'], 'us,ru,sk'.",
        ),
        (
            'model',
            None,
            "Specifies the name of the keyboard model used to determine"
            " the components which make up the keyboard description."
            " For example: 'pc101', 'pc105'.",
        ),
        (
            'option',
            None,
            "Specifies the name of an option to determine the"
            " components which make up the keyboard description. For"
            " example: ['compose:menu', 'grp_led:scroll'],"
            " 'compose:menu,grp_led:scroll'.",
        ),
        (
            'rules',
            None,
            "Specifies the name of the rules file used to resolve the"
            " requested layout and model to a set of component names.",
        ),
        (
            'symbols',
            None,
            "Specifies the name of the symbols component used to"
            " construct a keyboard layout.",
        ),
        (
            'synch',
            False,
            "Force synchronization for X requests.",
        ),
        (
            'types',
            None,
            "Specifies the name of the types component used to"
            " construct a keyboard layout.",
        ),
        (
            'variant',
            None,
            "Specifies which variant of the keyboard layout should be"
            " used to determine the components which make up the"
            " keyboard description.",
        ),
    ]

    def __init__(self, **config) -> None:
        # Instead of `base.InLoopPollText.__init__(self, **config)` to avoid
        # adding 'update_interval' to default values.
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(self.defaults)
        self.raise_for_dependencies()
        self.use_optional_dependencies_if_available()

        asyncio.ensure_future(self.loop())
        self.add_callbacks({'Button1': self.next_keyboard_layout_group})

    def raise_for_dependencies(self) -> None:
        """
        Raises NoDependencyFoundError if at least one dependency was not
        found
        """
        try:
            self.call_process(['xkb-switch', '-v'])
        except FileNotFoundError as e:
            err_msg = "Please, check that xkb-switch is available (%s)"
            logger.error(err_msg, e)
            raise NoDependencyFoundError(err_msg % e) from None

    def use_optional_dependencies_if_available(self) -> None:
        """
        Checks for optional dependencies and uses them if any.  If they
        aren't present and there is an attempt to use them then a
        corresponding message is added to the logs.  If they aren't in
        the system and there is no attempt to use them then nothing will
        happen.
        """
        parameter_names = [i[0] for i in self.defaults]
        parameter_values = [
            getattr(self, name) for name in parameter_names
        ]
        parameters = {
            name: value
            for name, value in zip(parameter_names, parameter_values)
            if value
        }
        try:
            self.call_process(['setxkbmap', '-version'])
        except FileNotFoundError:
            if parameters:
                logger.warning(
                    "To use the %s parameter(s) you need setxkbmap to be"
                    " available in the system.",
                    ", ".join(parameters)
                )
        else:
            self._use_setxkbmap(parameters)

    def _use_setxkbmap(self, parameters: dict) -> None:
        self.dirs: Union[list, tuple, str]
        self.layout_groups: Union[list, tuple, str]
        exclude_parameters = ('config_file', 'dirs', 'layout_groups', 'synch')
        for name, value in parameters.items():
            if name not in exclude_parameters:
                if isinstance(value, (list, tuple)):
                    setattr(self, name, ','.join(value))
                    value = getattr(self, name)
                try:
                    self.call_process(['setxkbmap', f'-{name}', value])
                except CalledProcessError as e:
                    logger.error(
                        "Invalid arguments passed for %s (%s)", name, e
                    )
        if self.config_file:
            try:
                self.call_process(['setxkbmap', '-config', self.config_file])
            except CalledProcessError as e:
                logger.error(
                    "Invalid arguments passed for config_file (%s)", e
                )
        if self.dirs:
            if isinstance(self.dirs, (list, tuple)):
                self.dirs = ' -I '.join(self.dirs)
            if isinstance(self.dirs, str):
                try:
                    self.call_process(['setxkbmap', '-I ' + self.dirs])
                except CalledProcessError as e:
                    logger.error("Invalid arguments passed for dirs (%s)", e)
            else:
                logger.error(
                    "dirs argument must be list, tuple or string, not %s",
                    type(self.dirs),
                )
        if self.layout_groups:
            if isinstance(self.layout_groups, (list, tuple)):
                self.layout_groups = ','.join(self.layout_groups)
            try:
                self.call_process(['setxkbmap', '-layout', self.layout_groups])
            except CalledProcessError as e:
                logger.error(
                    "Invalid arguments passed for layout_groups (%s)", e
                )
        if self.synch:
            self.call_process(['setxkbmap', '-synch'])

    async def loop(self) -> NoReturn:
        """
        An endless loop that updates the text when the group of the
        current layout is updated
        """
        self.tick()
        while True:
            event = await asyncio.create_subprocess_exec('xkb-switch', '-w')
            await event.wait()
            self.tick()

    @property
    def current_keyboard_layout_group(self) -> str:
        """Return the current keyboard layout group

        Examples: 'us', 'ru', 'sk'.  In case of error returns 'unknown'.
        """
        try:
            return self.call_process(['xkb-switch', '-p']).rstrip()
        except CalledProcessError as e:
            logger.error("Can't get the keyboard layout (%s)", e)
        return 'unknown'

    def next_keyboard_layout_group(self) -> None:
        """Switch to the next keyboard layout group"""
        try:
            self.call_process(['xkb-switch', '-n'])
        except CalledProcessError as e:
            logger.error("Can't set the keyboard layout (%s)", e)

    def poll(self) -> str:
        """Return the current keyboard layout group"""
        return self.current_keyboard_layout_group

    def timer_setup(self):
        # Do not use interval update `base.InLoopPollText.timer_setup`, events
        # are used instead.
        pass

    def button_press(self, x, y, button):
        # To avoid unnecessary calling `self.tick`.
        return base.InLoopPollText.button_press(self, x, y, button)
