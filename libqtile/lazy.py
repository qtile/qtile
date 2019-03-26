# Copyright (c) 2019, Sean Vig. All rights reserved.
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

from libqtile.command_graph import CommandGraphCall, CommandGraphRoot, CommandGraphObject, GraphType
from libqtile.command_client import SelectError


class LazyGraph:
    def __init__(self, *, node: GraphType = None):
        if node is None:
            self._current_node = CommandGraphRoot()  # type: GraphType
        else:
            self._current_node = node

    def __getattr__(self, name:  str) -> "LazyGraph":
        """Get the child element of the currently selected object"""
        if isinstance(self._current_node, CommandGraphCall):
            raise SelectError("Cannot select children of call", name, self._current_node.selectors)

        if name in self._current_node.children:
            next_node = self._current_node.navigate(name, None)
        else:
            next_node = self._current_node.call(name)

        return self.__class__(node=next_node)

    def __getitem__(self, name: str) -> "LazyGraph":
        """Get the selected element of the currently selected object"""
        if not isinstance(self._current_node, CommandGraphObject):
            raise SelectError("Unable to make selection on current node", name, self._current_node.selectors)

        if self._current_node.selector is not None:
            raise SelectError("Selection already made", name, self._current_node.selectors)

        next_node = self._current_node.parent.navigate(self._current_node.object_type, name)

        return self.__class__(node=next_node)


lazy = LazyGraph()
