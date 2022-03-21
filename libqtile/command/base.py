# Copyright (c) 2019 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the \"Software\"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
The objects in the command graph and command resolution on the objects
"""

from __future__ import annotations

import abc
import inspect
import traceback
from typing import TYPE_CHECKING

from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Callable, Optional

    from libqtile.command.graph import SelectorType

    ItemT = Optional[tuple[bool, list[str | int]]]


class SelectError(Exception):
    """Error raised in resolving a command graph object"""

    def __init__(self, err_string: str, name: str, selectors: list[SelectorType]):
        super().__init__("{}, name: {}, selectors: {}".format(err_string, name, selectors))
        self.name = name
        self.selectors = selectors


class CommandError(Exception):
    """Error raised in resolving a command"""


class CommandException(Exception):
    """Error raised while executing a command"""


class CommandObject(metaclass=abc.ABCMeta):
    """Base class for objects that expose commands

    Each command should be a method named `cmd_X`, where X is the command name.
    A CommandObject should also implement `._items()` and `._select()` methods
    (c.f. docstring for `.items()` and `.select()`).
    """

    def select(self, selectors: list[SelectorType]) -> CommandObject:
        """Return a selected object

        Recursively finds an object specified by a list of `(name, selector)`
        items.

        Raises SelectError if the object does not exist.
        """
        obj: CommandObject = self
        for name, selector in selectors:
            root, items = obj.items(name)
            # if non-root object and no selector given
            if root is False and selector is None:
                raise SelectError("", name, selectors)
            # if no items in container, but selector is given
            if items is None and selector is not None:
                raise SelectError("", name, selectors)
            # if selector is not in the list of contained items
            if items is not None and selector and selector not in items:
                raise SelectError("", name, selectors)

            maybe_obj = obj._select(name, selector)
            if maybe_obj is None:
                raise SelectError("", name, selectors)
            obj = maybe_obj
        return obj

    def items(self, name: str) -> tuple[bool, list[str | int] | None]:
        """Build a list of contained items for the given item class

        Returns a tuple `(root, items)` for the specified item class, where:

            root: True if this class accepts a "naked" specification without an
            item seletion (e.g. "layout" defaults to current layout), and False
            if it does not (e.g. no default "widget").

            items: a list of contained items
        """
        ret = self._items(name)
        if ret is None:
            # Not finding information for a particular item class is OK here;
            # we don't expect layouts to have a window, etc.
            return False, None
        return ret

    @abc.abstractmethod
    def _items(self, name) -> ItemT:
        """Generate the items for a given

        Same return as `.items()`. Return `None` if name is not a valid item
        class.
        """

    @abc.abstractmethod
    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        """Select the given item of the given item class

        This method is called with the following guarantees:
            - `name` is a valid selector class for this item
            - `sel` is a valid selector for this item
            - the `(name, sel)` tuple is not an "impossible" combination (e.g. a
              selector is specified when `name` is not a containment object).

        Return None if no such object exists
        """

    def command(self, name: str) -> Callable | None:
        """Return the command with the given name

        Parameters
        ----------
        name: str
            The name of the command to fetch.

        Returns
        -------
        Callable
            The command function that can be invoked.
        """
        return getattr(self, "cmd_" + name, None)

    @property
    def commands(self) -> list[str]:
        """All of the commands on the given object"""
        cmds = [i[4:] for i in dir(self) if i.startswith("cmd_")]
        return cmds

    def cmd_commands(self) -> list[str]:
        """Returns a list of possible commands for this object

        Used by __qsh__ for command completion and online help
        """
        return self.commands

    def cmd_items(self, name) -> tuple[bool, list[str | int] | None]:
        """Returns a list of contained items for the specified name

        Used by __qsh__ to allow navigation of the object graph.
        """
        return self.items(name)

    def cmd_doc(self, name) -> str:
        """Returns the documentation for a specified command name

        Used by __qsh__ to provide online help.
        """
        if name in self.commands:
            command = self.command(name)
            assert command
            signature = self._get_command_signature(command)
            spec = name + signature
            htext = inspect.getdoc(command) or ""
            return spec + "\n" + htext
        raise CommandError("No such command: %s" % name)

    def _get_command_signature(self, command: Callable) -> str:
        signature = inspect.signature(command)
        args = list(signature.parameters)
        if args and args[0] == "self":
            args = args[1:]
            parameters = [signature.parameters[arg] for arg in args]
            signature = signature.replace(parameters=parameters)
        return str(signature)

    def cmd_eval(self, code: str) -> tuple[bool, str | None]:
        """Evaluates code in the same context as this function

        Return value is tuple `(success, result)`, success being a boolean and
        result being a string representing the return value of eval, or None if
        exec was used instead.
        """
        try:
            try:
                return True, str(eval(code))
            except SyntaxError:
                exec(code)
                return True, None
        except Exception:
            error = traceback.format_exc().strip().split("\n")[-1]
            return False, error

    def cmd_function(self, function, *args, **kwargs) -> None:
        """Call a function with current object as argument"""
        try:
            function(self, *args, **kwargs)
        except Exception:
            error = traceback.format_exc()
            logger.error('Exception calling "%s":\n%s', function, error)
