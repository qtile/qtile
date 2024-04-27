# Copyright (c) 2019 Sean Vig
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

"""
The interface to execute commands on the command graph
"""

from __future__ import annotations

import traceback
import types
import typing
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Union, get_args, get_origin

from libqtile import ipc
from libqtile.command.base import CommandError, CommandException, CommandObject, SelectError
from libqtile.command.graph import CommandGraphCall, CommandGraphNode
from libqtile.log_utils import logger
from libqtile.utils import ColorsType, ColorType  # noqa: F401

if TYPE_CHECKING:
    from libqtile.command.graph import SelectorType

SUCCESS = 0
ERROR = 1
EXCEPTION = 2


# these two mask their aliases from elsewhere in the tree (i.e.
# libqtile.extension.base._Extension, and libqtile.layout.base.Layout
#
# since neither of these have constructors from a single string, we can't
# really lift them to a type. probably nobody actually passes us layouts here
# so it doesn't matter, but in the event that it does, we can probably fix it
# up with some eval() hackery whackery.
class _Extension:
    pass


class Layout:
    pass


def format_selectors(selectors: list[SelectorType]) -> str:
    """Build the path to the selected command graph node"""
    path_elements = []
    for name, selector in selectors:
        if selector is not None:
            path_elements.append("{}[{}]".format(name, selector))
        else:
            path_elements.append(name)
    return ".".join(path_elements)


class CommandInterface(metaclass=ABCMeta):
    """Defines an interface which can be used to evaluate a given call on a command graph.

    The implementations of this may use, for example, an IPC call to access the
    running qtile instance remotely or directly access the qtile instance from
    within the same process, or it may return lazily evaluated results.
    """

    @abstractmethod
    def execute(self, call: CommandGraphCall, args: tuple, kwargs: dict) -> Any:
        """Execute the given call, returning the result of the execution

        Perform the given command graph call, calling the function with the
        given arguments and keyword arguments.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """

    @abstractmethod
    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for commands
        command: str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """

    @abstractmethod
    def has_item(self, node: CommandGraphNode, object_type: str, item: str | int) -> bool:
        """Check if the given item exists

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for items
        object_type: str
            The type of object to check for items.
        command: str
            The name of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """


class QtileCommandInterface(CommandInterface):
    """Execute the commands via the in process running qtile instance"""

    def __init__(self, command_object: CommandObject):
        """A command object that directly resolves commands

        Parameters
        ----------
        command_object: CommandObject
            The command object to use for resolving the commands and items
            against.
        """
        self._command_object = command_object

    def execute(self, call: CommandGraphCall, args: tuple, kwargs: dict) -> Any:
        """Execute the given call, returning the result of the execution

        Perform the given command graph call, calling the function with the
        given arguments and keyword arguments.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """
        obj = self._command_object.select(call.selectors)
        cmd = None
        try:
            cmd = obj.command(call.name)
        except SelectError:
            pass

        if cmd is None:
            return "No such command."

        logger.debug("Command: %s(%s, %s)", call.name, args, kwargs)
        return cmd(self._command_object, *args, **kwargs)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for commands
        command: str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """
        obj = self._command_object.select(node.selectors)
        cmd = obj.command(command)
        return cmd is not None

    def has_item(self, node: CommandGraphNode, object_type: str, item: str | int) -> bool:
        """Check if the given item exists

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for items
        object_type: str
            The type of object to check for items.
        item: str
            The name or index of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """
        try:
            self._command_object.select(node.selectors + [(object_type, item)])
        except SelectError:
            return False
        return True


class IPCCommandInterface(CommandInterface):
    """Execute the resolved commands using the IPC connection to a running qtile instance"""

    def __init__(self, ipc_client: ipc.Client):
        """Build a command object which resolves commands through IPC calls

        Parameters
        ----------
        ipc_client: ipc.Client
            The client that is to be used to resolve the calls.
        """
        self._client = ipc_client

    def execute(self, call: CommandGraphCall, args: tuple, kwargs: dict) -> Any:
        """Execute the given call, returning the result of the execution

        Executes the given command over the given IPC client.  Returns the
        result of the execution.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """
        status, result = self._client.send(
            (call.parent.selectors, call.name, args, kwargs, call.lifted)
        )
        if status == SUCCESS:
            return result
        if status == ERROR:
            raise CommandError(result)
        raise CommandException(result)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Resolves the allowed commands over the IPC interface, and returns a
        boolean indicating of the given command is valid.

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for commands
        command: str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """
        cmd_call = node.call("commands")
        commands = self.execute(cmd_call, (), {})
        return command in commands

    def has_item(self, node: CommandGraphNode, object_type: str, item: str | int) -> bool:
        """Check if the given item exists

        Resolves the available commands for the given command node of the given
        command type.  Performs the resolution of the items through the given
        IPC client.

        Parameters
        ----------
        node: CommandGraphNode
            The node to check for items
        object_type: str
            The type of object to check for items.
        command: str
            The name of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """
        items_call = node.call("items")
        _, items = self.execute(items_call, (object_type,), {})
        return items is not None and item in items


def lift_args(cmd, args, kwargs):
    """
    Lift args lifts the arguments to the type annotations on cmd's parameters.
    """

    def lift_arg(typ, arg):
        # for stuff like int | None, allow either
        if get_origin(typ) in [types.UnionType, Union]:
            for t in get_args(typ):
                if t == types.NoneType:
                    # special case None? I don't know what this looks like
                    # coming over IPC
                    if arg == "":
                        return None
                    if arg is None:
                        return None
                    continue

                try:
                    return lift_arg(t, arg)
                except TypeError:
                    pass
            # uh oh, we couldn't lift it to anything
            raise TypeError(f"{arg} is not a {typ}")

        # for literals, check that it is one of the valid strings
        if get_origin(typ) is Literal:
            if arg not in get_args(typ):
                raise TypeError(f"{arg} is not one of {get_origin(typ)}")
            return arg

        if typ is bool:
            # >>> bool("False") is True
            # True
            # ... but we want it to be false :)
            if arg == "True" or arg is True:
                return True
            if arg == "False" or arg is False:
                return False
            raise TypeError(f"{arg} is not a bool")

        if typ is Any:
            # can't do any lifting if we don't know the type
            return arg

        if typ in [_Extension, Layout]:
            # these are "complex" objects that can't be created with a
            # single string argument. we generally don't expect people to
            # be passing these over the command line, so let's ignore then.
            return arg

        if get_origin(typ) in [list, dict]:
            # again, we do not want to be in the business of parsing
            # lists/dicts of types out of strings; just pass on whatever we
            # got
            return arg

        return typ(arg)

    converted_args = []
    converted_kwargs = dict()

    params = typing.get_type_hints(cmd, globalns=globals())

    non_return_annotated_args = filter(lambda k: k != "return", params.keys())
    for param, arg in zip(non_return_annotated_args, args):
        converted_args.append(lift_arg(params[param], arg))

    # if not all args were annotated, we need to keep them anyway. note
    # that mixing some annotated and not annotated args will not work well:
    # we will reorder args here and cause problems. this is solveable but
    # somewhat ugly, and we can avoid it by always annotating all
    # parameters.
    #
    # if we really want to fix this, we
    # inspect.signature(foo).parameters.keys() gives us the ordered
    # parameters to reason about.
    if len(converted_args) < len(args):
        converted_args.extend(args[len(converted_args) :])

    for k, v in kwargs.items():
        # if this kwarg has a type annotation, use it
        if k in params:
            converted_kwargs[k] = lift_arg(params[k], v)
        else:
            converted_kwargs[k] = v

    return tuple(converted_args), converted_kwargs


class IPCCommandServer:
    """Execute the object commands for the calls that are sent to it"""

    def __init__(self, qtile) -> None:
        """Wrapper around the ipc server for communitacing with the IPCCommandInterface

        sets up the IPC server such that it will receive and send messages to
        and from the IPCCommandInterface.
        """
        self.qtile = qtile

    def call(
        self,
        data: tuple[list[SelectorType], str, tuple, dict, bool],
    ) -> tuple[int, Any]:
        """Receive and parse the given data"""
        selectors, name, args, kwargs, lifted = data
        try:
            obj = self.qtile.select(selectors)
            cmd = obj.command(name)
        except SelectError as err:
            sel_string = format_selectors(selectors)
            return ERROR, "No object {} in path '{}'".format(err.name, sel_string)
        if not cmd:
            return ERROR, "No such command"

        logger.debug("Command: %s(%s, %s)", name, args, kwargs)

        if lifted:
            args, kwargs = lift_args(cmd, args, kwargs)

        # Check if method is bound, if itis, insert magic self
        if not hasattr(cmd, "__self__"):
            args = (obj,) + args

        try:
            return SUCCESS, cmd(*args, **kwargs)
        except CommandError as err:
            return ERROR, err.args[0]
        except Exception:
            return EXCEPTION, traceback.format_exc()
