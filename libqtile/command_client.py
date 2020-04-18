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
The clients that expose the command graph of a given command interface

The clients give the ability to navigate the command graph while providing name
resolution with the given command graph interface.  When writing functionality
that interacts with qtile objects, it should favor using the command graph
clients to do this interaction.
"""

from typing import Any, List, Optional, Union

from libqtile.command_graph import (
    CommandGraphCall,
    CommandGraphNode,
    CommandGraphObject,
    CommandGraphRoot,
    GraphType,
)
from libqtile.command_interface import CommandInterface, IPCCommandInterface
from libqtile.command_object import SelectError
from libqtile.ipc import Client, find_sockfile


class CommandClient:
    """The object that resolves the commands"""

    def __init__(self, command: CommandInterface = None, *, current_node: GraphType = None) -> None:
        """A client that resolves calls through the command object interface

        Exposes a similar API to the command graph, but performs resolution of
        objects.  Any navigation done on the command graph is resolved at the
        point it is invoked.  This command resolution is done via the command
        interface.

        Parameters
        ----------
        command: CommandInterface
            The object that is used to resolve command graph calls, as well as
            navigate the command graph.
        current_node: CommandGraphNode
            The current node that is pointed to in the command graph.  If not
            specified, the command graph root is used.
        """
        if command is None:
            command = IPCCommandInterface(Client(find_sockfile()))
        self._command = command
        if current_node is None:
            self._current_node = CommandGraphRoot()  # type: GraphType
        else:
            self._current_node = current_node

    def __call__(self, *args, **kwargs) -> Any:
        """When the client has navigated to a command, execute it"""
        if not isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Invalid call", "", self._current_node.selectors)

        return self._command.execute(self._current_node, args, kwargs)

    def navigate(self, name: str, selector: Optional[str]) -> "CommandClient":
        """Resolve the given object in the command graph

        Parameters
        ----------
        name : str
            The name of the command graph object to resolve.
        selector : Optional[str]
            If given, the selector to use to select the next object, and if
            None, then selects the default object.

        Returns
        -------
        CommandClient
            The client with the given command graph object resolved.
        """
        if not isinstance(self._current_node, CommandGraphNode):
            raise SelectError("Invalid navigation", "", self._current_node.selectors)

        if name not in self.children:
            raise SelectError("Not valid child", name, self._current_node.selectors)
        if selector is not None:
            if self._command.has_item(self._current_node, name, selector):
                raise SelectError("Item not available in object", name, self._current_node.selectors)

        next_node = self._current_node.navigate(name, selector)
        return self.__class__(self._command, current_node=next_node)

    def call(self, name: str) -> "CommandClient":
        """Resolve the call into the command graph

        Parameters
        ----------
        name : str
            The name of the command to resolve in the command graph.

        Returns
        -------
        CommandClient
            The client with the command resolved.
        """
        if not isinstance(self._current_node, CommandGraphNode):
            raise SelectError("Invalid navigation", "", self._current_node.selectors)

        command_call = self._current_node.call("commands")
        commands = self._command.execute(command_call, (), {})
        if name not in commands:
            raise SelectError("Not valid child or command", name, self._current_node.selectors)
        next_node = self._current_node.call(name)
        return self.__class__(self._command, current_node=next_node)

    @property
    def children(self) -> List[str]:
        """Get the children of the current location in the command graph"""
        if isinstance(self._current_node, CommandGraphCall):
            raise SelectError("No children of command graph call", "", self._current_node.selectors)
        return self._current_node.children

    @property
    def root(self) -> "CommandClient":
        """Get the root of the command graph"""
        return self.__class__(self._command)

    @property
    def parent(self) -> "CommandClient":
        """Get the parent of the current client"""
        if self._current_node.parent is None:
            raise SelectError("", "", self._current_node.selectors)
        return self.__class__(self._command, current_node=self._current_node.parent)


class InteractiveCommandClient:
    """
    A command graph client that can be used to easily resolve elements interactively
    """

    def __init__(self, command: CommandInterface = None, *, current_node: GraphType = None) -> None:
        """An interactive client that resolves calls through the gives client

        Exposes the command graph API in such a way that it can be traversed
        directly on this object.  The command resolution for this object is
        done via the command interface.

        Parameters
        ----------
        command: CommandInterface
            The object that is used to resolve command graph calls, as well as
            navigate the command graph.
        current_node: CommandGraphNode
            The current node that is pointed to in the command graph.  If not
            specified, the command graph root is used.
        """
        if command is None:
            command = IPCCommandInterface(Client(find_sockfile()))
        self._command = command
        if current_node is None:
            self._current_node = CommandGraphRoot()  # type: GraphType
        else:
            self._current_node = current_node

    def __call__(self, *args, **kwargs) -> Any:
        """When the client has navigated to a command, execute it"""
        if not isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Invalid call", "", self._current_node.selectors)

        return self._command.execute(self._current_node, args, kwargs)

    def __getattr__(self, name: str) -> "InteractiveCommandClient":
        """Get the child element of the currently selected object

        Resolve the element specified by the given name, either the child
        object, or the command on the current object.

        Parameters
        ----------
        name : str
            The name of the element to resolve

        Return
        ------
        InteractiveCommandClient
            The client navigated to the specified name.  Will respresent either
            a command graph node (if the name is a valid child) or a command
            graph call (if the name is a valid command).
        """
        if isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Cannot select children of call", name, self._current_node.selectors)

        # we do not know if the name is a command to be executed, or an object
        # to navigate to
        if name not in self._current_node.children:
            # we are going to resolve a command, check that the command is valid
            if not self._command.has_command(self._current_node, name):
                raise SelectError("Not valid child or command", name, self._current_node.selectors)
            call_object = self._current_node.call(name)
            return self.__class__(self._command, current_node=call_object)

        next_node = self._current_node.navigate(name, None)
        return self.__class__(self._command, current_node=next_node)

    def __getitem__(self, name: Union[str, int]) -> "InteractiveCommandClient":
        """Get the selected element of the currently selected object

        From the current command graph object, select the instance with the
        given name.

        Parameters
        ----------
        name : str
            The name, or index if it's of int type, of the item to resolve

        Return
        ------
        InteractiveCommandClient
            The current client, navigated to the specified command graph
            object.
        """
        if isinstance(self._current_node, CommandGraphRoot):
            raise KeyError("Root node has no available items",
                           name, self._current_node.selectors)

        if not isinstance(self._current_node, CommandGraphObject):
            raise SelectError("Unable to make selection on current node",
                              str(name), self._current_node.selectors)

        if self._current_node.selector is not None:
            raise SelectError("Selection already made", str(name),
                              self._current_node.selectors)

        # check the selection is valid in the server-side qtile manager
        if not self._command.has_item(self._current_node.parent,
                                      self._current_node.object_type, name):
            raise SelectError("Item not available in object",
                              str(name), self._current_node.selectors)

        next_node = self._current_node.parent.navigate(self._current_node.object_type, name)
        return self.__class__(self._command, current_node=next_node)

    def normalize_item(self, item: Union[str, int]) -> Union[str, int]:
        "Normalize the item according to Qtile._items()."
        object_type = self._current_node.object_type \
            if isinstance(self._current_node, CommandGraphObject) else None
        if object_type in ["group", "widget", "bar"]:
            return str(item)
        elif object_type in ["layout", "window", "screen"]:
            return int(item)
        else:
            return item
