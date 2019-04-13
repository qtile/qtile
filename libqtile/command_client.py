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

from typing import Any, List, Optional

from libqtile.command_graph import (
    CommandGraphCall,
    CommandGraphNode,
    CommandGraphObject,
    CommandGraphRoot,
    GraphType,
    SelectorType,
)
from libqtile.command_interface import CommandInterface


class CommandError(Exception):
    pass


class CommandException(Exception):
    pass


class SelectError(Exception):
    def __init__(self, err_string: str, name: str, selectors: List[SelectorType]):
        super().__init__(err_string)
        self.name = name
        self.selectors = selectors


class CommandClient:
    def __init__(self, command: CommandInterface, *, current_node: GraphType = None) -> None:
        """A client that resolves calls through the gives client

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
        if not isinstance(self._current_node, CommandGraphNode):
            raise SelectError("Invalid navigation", "", self._current_node.selectors)

        if name not in self._current_node.children:
            raise SelectError("Not valid child", name, self._current_node.selectors)
        if selector is not None and not self._command.has_item(self._current_node, name, selector):
            raise SelectError("No items in object", name, self._current_node.selectors)

        next_node = self._current_node.navigate(name, selector)
        return self.__class__(self._command, current_node=next_node)

    def call(self, name: str) -> "CommandClient":
        if not isinstance(self._current_node, CommandGraphNode):
            raise SelectError("Invalid navigation", "", self._current_node.selectors)

        command_call = self._current_node.call("commands")
        commands = self._command.execute(command_call, (), {})
        if name not in commands:
            raise SelectError("Not valid child or command", name, self._current_node.selectors)
        next_node = self._current_node.call(name)
        return self.__class__(self._command, current_node=next_node)


class InteractiveCommandClient:
    def __init__(self, command: CommandInterface, *, current_node: GraphType = None) -> None:
        """An interactive client that resolves calls through the gives client

        Exposes the command graph API in such a way that it can be traversed
        directly on this object.  The command resolution for this object is
        done via the command interface.

        Parameters
        ----------
        command: InteractiveCommandInterface
            The object that is used to resolve command graph calls, as well as
            navigate the command graph.
        current_node: CommandGraphNode
            The current node that is pointed to in the command graph.  If not
            specified, the command graph root is used.
        """
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

    def __getattr__(self, name:  str) -> "InteractiveCommandClient":
        """Get the child element of the currently selected object"""
        if isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Cannot select children of call", name, self._current_node.selectors)

        if name not in self._current_node.children:
            # we are gaing to resolve a command, check that the command is valid
            if not self._command.has_command(self._current_node, name):
                raise SelectError("Not valid child or command", name, self._current_node.selectors)
            next_node = self._current_node.call(name)  # type: GraphType
        else:
            next_node = self._current_node.navigate(name, None)

        return self.__class__(self._command, current_node=next_node)

    def __getitem__(self, name: str) -> "InteractiveCommandClient":
        """Get the selected element of the currently selected object"""
        if not isinstance(self._current_node, CommandGraphObject):
            raise SelectError("Unable to make selection on current node", name, self._current_node.selectors)

        if self._current_node.selector is not None:
            raise SelectError("Selection already made", name, self._current_node.selectors)

        # check that the selection is valid
        if not self._command.has_item(self._current_node.parent, self._current_node.object_type, name):
            raise SelectError("No items in object", name, self._current_node.selectors)

        next_node = self._current_node.parent.navigate(self._current_node.object_type, name)
        return self.__class__(self._command, current_node=next_node)
