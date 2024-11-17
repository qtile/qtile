# Copyright (c) 2017 Dario Giovannetti
# Copyright (c) 2021 elParaguayo
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
from subprocess import PIPE, Popen
from typing import Any

from libqtile import configurable
from libqtile.log_utils import logger


class _Extension(configurable.Configurable):
    """Base Extension class"""

    installed_extensions = []  # type: list

    defaults: list[tuple[str, Any, str]] = []

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_Extension.defaults)
        _Extension.installed_extensions.append(self)

    def _configure(self, qtile) -> None:
        self.qtile = qtile

    def run(self):
        """
        This method must be implemented by the subclasses.
        """
        raise NotImplementedError()


class RunCommand(_Extension):
    """
    Run an arbitrary command.

    Mostly useful as a superclass for more specific extensions that need to
    interact with the qtile object.

    Also consider simply using lazy.spawn() or writing a
    `client <https://docs.qtile.org/en/latest/manual/commands/advanced.html#client-server-scripting-model>`_.
    """

    defaults: list[tuple[str, Any, str]] = [
        # NOTE: Do not use a list as a default value, since it would be shared
        #       among all the objects inheriting this class, and if one of them
        #       modified it, all the other objects would see the modified list;
        #       use a string or a tuple instead, which are immutable
        ("command", None, "the command to be launched (string or list with arguments)"),
    ]

    def __init__(self, **config):
        _Extension.__init__(self, **config)
        self.add_defaults(RunCommand.defaults)
        self.configured_command = None

    def run(self) -> Popen:
        """
        An extension can inherit this class, define configured_command and use
        the process object by overriding this method and using super():

        .. code-block:: python

            def _configure(self, qtile):
                Superclass._configure(self, qtile)
                self.configured_command = "foo --bar"

            def run(self):
                process = super(Subclass, self).run()
        """
        if self.configured_command:
            if isinstance(self.configured_command, str):
                self.configured_command = shlex.split(self.configured_command)
            # Else assume that self.configured_command is already a sequence
        else:
            self.configured_command = self.command
        return Popen(self.configured_command, stdout=PIPE, stdin=PIPE)
