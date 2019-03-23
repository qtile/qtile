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

from typing import Any, Dict, List, Tuple

from libqtile import ipc
from libqtile.command_graph import (
    _CommandGraphNode,
    CommandGraphCall,
    CommandGraphContainer,
    CommandGraphObject,
    CommandGraphRoot,
    SelectorType,
)


class CommandError(Exception):
    pass


class CommandException(Exception):
    pass


class SelectError(Exception):
    def __init__(self, err_string: str, name: str, selectors: List[SelectorType]):
        super().__init__(err_string)
        self.name = name
        self.selectors = selectors


class Client:
    def __init__(self, ipc_client: ipc.Client, *, current_node: _CommandGraphNode = None) -> None:
        """A client that resolves calls through the gives IPC client

        Exposes a similar API to the command graph, but only elements in the
        command graph that exist in the command graph hooked to the IPC client.
        Resolves calls through the IPC client.

        Parameters
        ----------
        ipc_client: ipc.Client
            The IPC client that is used to resolve command graph calls, as well
            as navigate the command graph.
        current_node: _CommandGraphNode
            The current node that is pointed to in the command graph.
        """
        self._client = ipc_client
        if current_node is None:
            self._current_node = CommandGraphRoot()  # type: _CommandGraphNode
        else:
            self._current_node = current_node

    def _execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> Any:
        """Execute the given command graph call and return the result"""
        status, result = self._client.send((
            call.parent.selectors, call.name, args, kwargs
        ))
        if status == 0:
            return result
        elif status == 1:
            raise CommandError(result)
        else:
            raise CommandException(result)

    def __call__(self, *args, **kwargs) -> Any:
        """When the client has navigated to a command, execute it"""
        if not isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Invalid call", "", self._current_node.selectors)

        if self._current_node.parent.selector is None:
            # TODO: check that there is a default object when no selector is given
            pass

        return self._execute(self._current_node, args, kwargs)

    def __getattr__(self, name:  str) -> "Client":
        """Get the child element of the currently selected object"""
        if not isinstance(self._current_node, CommandGraphContainer):
            raise SelectError("Cannot access children of node", name, self._current_node.selectors)

        if name not in self._current_node.children:
            # we are gaing to resolve a command, check that the command is valid
            cmd_call = self._current_node.navigate("commands", None)
            assert isinstance(cmd_call, CommandGraphCall)
            commands = self._execute(cmd_call, (), {})
            if name not in commands:
                raise SelectError("Not valid child or command", name, self._current_node.selectors)

        next_node = self._current_node.navigate(name, None)
        return self.__class__(self._client, current_node=next_node)

    def __getitem__(self, name: str) -> "Client":
        """Get the selected element of the currently selected object"""
        if not isinstance(self._current_node, CommandGraphObject):
            raise SelectError("Unable to make selection on current node", name, self._current_node.selectors)

        if self._current_node.selector is not None:
            raise SelectError("Selection already made", name, self._current_node.selectors)

        # check that the selection is valid
        items_call = self._current_node.parent.navigate("items", None)
        assert isinstance(items_call, CommandGraphCall)
        _, items = self._execute(items_call, (self._current_node.object_type,), {})
        if items is None:
            raise SelectError("No items in object", name, self._current_node.selectors)
        if name not in items:
            err_str = "Available items: {}".format(",".join(map(str, items)))
            raise SelectError(err_str, name, self._current_node.selectors)

        next_node = self._current_node.parent.navigate(
            self._current_node.object_type, name
        )
        return self.__class__(self._client, current_node=next_node)
