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
import asyncio
import inspect
import sys
import traceback
from functools import partial
from typing import TYPE_CHECKING

from libqtile.configurable import Configurable
from libqtile.log_utils import logger
from libqtile.utils import create_task

if TYPE_CHECKING:
    from collections.abc import Callable

    from libqtile.command.graph import SelectorType

    ItemT = tuple[bool, list[str | int]] | None


def expose_command(name: Callable | str | list[str] | None = None) -> Callable:
    """
    Decorator to expose methods to the command interface.

    The exposed command will have the name of the defined method.

    Methods can also be exposed via multiple names by passing the names to this
    decorator.

    e.g. if a layout wants "up" and "previous" to call the
    same method:

    @expose_command("previous")
    def up(self):
        ...

    `up` will be exposed as `up` and `previous`.

    Multiple names can be passed as a list.
    """

    def wrapper(func: Callable):
        setattr(func, "_cmd", True)
        if name is not None:
            if not hasattr(func, "_mapping"):
                setattr(func, "_mapping", list())
            if isinstance(name, list):
                func._mapping += name  # type:ignore
            elif isinstance(name, str):
                func._mapping.append(name)  # type:ignore
            else:
                logger.error("Unexpected value received in command decorator: %s", name)
        return func

    # If the decorator is added with no parentheses then we should treat it
    # as if it had been i.e. expose the decorated method
    if callable(name):
        func = name
        name = None
        return wrapper(func)

    return wrapper


class SelectError(Exception):
    """Error raised in resolving a command graph object"""

    def __init__(self, err_string: str, name: str, selectors: list[SelectorType]):
        super().__init__(f"{err_string}, name: {name}, selectors: {selectors}")
        self.name = name
        self.selectors = selectors


class CommandError(Exception):
    """Error raised in resolving a command"""


class CommandException(Exception):
    """Error raised while executing a command"""


class CommandObject(metaclass=abc.ABCMeta):
    """Base class for objects that expose commands

    Any command to be exposed should be decorated with
    `@expose_command()` (classes that are not explicitly
    inheriting from CommandObject will need to import the module)
    A CommandObject should also implement `._items()` and `._select()` methods
    (c.f. docstring for `.items()` and `.select()`).
    """

    def __new__(cls, *args, **kwargs):
        # Check which level of command object has been parsed
        # This test ensures inherited classes don't stop additional
        # methods from being exposed.
        # For example, if widget.TextBox has already been parsed, a subsequent
        # call to initialise a new TextBox will return here. However, if a user
        # subclasses TextBox for a new widget then that new widget will still
        # be parsed here to check for new commands.
        if getattr(cls, "_command_object", "") == cls.__name__:
            super().__new__(cls)

        commands = {}
        cmd_s = set()

        # We need to iterate over the class's inherited classes in reverse order
        # We reverse the order so the exposed command will always be the latest
        # definition of the method.
        for c in reversed(list(cls.__mro__)):
            for method_name in list(c.__dict__.keys()):
                method = getattr(c, method_name, None)

                if method is None:
                    continue

                # If the command has been exposed, add it to our dictionary
                # If the method name is already in our dictionary then bind the
                # latest definition to that command
                if hasattr(method, "_cmd") or method_name in commands:
                    commands[method_name] = method
                # For now, we'll accept the old format `cmd_` naming scheme for
                # exposing commands.
                # NOTE: This will be deprecated in the future
                elif method_name.startswith("cmd_"):
                    cmd_s.add(method_name)
                    commands[method_name[4:]] = method

                # Expose additional names
                for mapping in getattr(method, "_mapping", list()):
                    setattr(cls, mapping, method)
                    commands[mapping] = method

        if cmd_s:
            names = ", ".join(cmd_s)
            msg = (
                f"The use of the 'cmd_' prefix to expose commands via IPC "
                f"is deprecated. Methods should use the "
                f"@expose_command() decorator instead. "
                f"Please update: {names}"
            )
            logger.warning("Deprecation Warning: %s", msg)

        # Record the object as being parsed.
        cls._command_object = cls.__name__

        # Store list of exposed commands
        cls._commands = commands

        return super().__new__(cls)

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

    @expose_command()
    def items(self, name: str) -> tuple[bool, list[str | int] | None]:
        """
        Build a list of contained items for the given item class.

        Exposing this allows __qsh__ to navigate the command graph.

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

        """
        return self._commands.get(name)

    def __getattr__(self, name):
        # We can use __getattr_ to handle deprecated calls to
        # cmd_ but we need to stop this overriding Configurable's
        # use of this method
        if isinstance(self, Configurable):
            try:
                return Configurable.__getattr__(self, name)
            except AttributeError:
                pass

        # It's not a Configurable attribute so let's check if it's
        # a command call
        if name.startswith("cmd_"):
            cmd = name[4:]
            if cmd in self.commands():
                logger.warning(
                    "Deprecation Warning: commands exposed via IPC no "
                    "longer use the 'cmd_' prefix. "
                    "Please replace '%s' with '%s' in your code.",
                    name,
                    cmd,
                )
                # This is not a bound method so we need to pass 'self'
                return partial(self.command(cmd), self)

        raise AttributeError(f"{self.__class__} has no attribute {name}")

    @expose_command()
    def commands(self) -> list[str]:
        """
        Returns a list of possible commands for this object

        Used by __qsh__ for command completion and online help
        """
        return sorted([cmd for cmd in self._commands])

    @expose_command()
    def doc(self, name) -> str:
        """Returns the documentation for a specified command name

        Used by __qsh__ to provide online help.
        """
        if name in self.commands():
            command = self.command(name)
            assert command
            signature = self._get_command_signature(command)
            spec = name + signature
            htext = inspect.getdoc(command) or ""
            return spec + "\n" + htext
        raise CommandError(f"No such command: {name}")

    def _get_command_signature(self, command: Callable) -> str:
        signature = inspect.signature(command)
        args = list(signature.parameters)
        if args and args[0] == "self":
            args = args[1:]
            parameters = [signature.parameters[arg] for arg in args]
            signature = signature.replace(parameters=parameters)
        return str(signature)

    @expose_command()
    def eval(self, code: str) -> tuple[bool, str | None]:
        """Evaluates code in the same context as this function

        Return value is tuple `(success, result)`, success being a boolean and
        result being a string representing the return value of eval, or None if
        exec was used instead.
        """
        try:
            globals_ = vars(sys.modules[self.__module__])
            try:
                return True, str(eval(code, globals_, locals()))
            except SyntaxError:
                exec(code, globals_, locals())
                return True, None
        except Exception:
            error = traceback.format_exc().strip().split("\n")[-1]
            return False, error

    @expose_command()
    def function(self, function, *args, **kwargs) -> asyncio.Task | None:
        """Call a function with current object as argument"""
        try:
            if asyncio.iscoroutinefunction(function):
                return create_task(function(self, *args, **kwargs))
            else:
                return function(self, *args, **kwargs)
        except Exception:
            error = traceback.format_exc()
            logger.error('Exception calling "%s":\n%s', function, error)
            return None
