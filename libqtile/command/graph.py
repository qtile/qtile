# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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
The objects defining the nodes in the command graph and the navigation of the
abstract command graph
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from typing import Optional, Type

    SelectorType = tuple[str, Optional[str | int]]


class CommandGraphNode(metaclass=abc.ABCMeta):
    """A container node in the command graph structure

    A command graph node which can contain other elements that it can link to.
    May also have commands that can be executed on itself.
    """

    @property
    @abc.abstractmethod
    def selector(self) -> str | int | None:
        """The selector for the current node"""

    @property
    @abc.abstractmethod
    def selectors(self) -> list[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""

    @property
    @abc.abstractmethod
    def parent(self) -> CommandGraphNode | None:
        """The parent of the current node"""

    @property
    @abc.abstractmethod
    def children(self) -> list[str]:
        """The child objects that are contained within this object"""

    def navigate(self, name: str, selector: str | int | None) -> CommandGraphNode:
        """Navigate from the current node to the specified child"""
        if name in self.children:
            return _COMMAND_GRAPH_MAP[name](selector, self)
        raise KeyError("Given node is not an object: {}".format(name))

    def call(self, name: str) -> CommandGraphCall:
        """Execute the given call on the selected object"""
        return CommandGraphCall(name, self)


class CommandGraphCall:
    """A call performed on a particular object in the command graph"""

    def __init__(self, name: str, parent: CommandGraphNode) -> None:
        """A command to be executed on the selected object

        A terminal node in the command graph, specifying an actual command to
        execute on the selected graph element.

        Parameters
        ----------
        name:
            The name of the command to execute
        parent:
            The command graph node on which to execute the given command.
        """
        self._name = name
        self._parent = parent

    @property
    def name(self) -> str:
        """The name of the call to make"""
        return self._name

    @property
    def selectors(self) -> list[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        return self.parent.selectors

    @property
    def parent(self) -> CommandGraphNode:
        """The parent of the current node"""
        return self._parent


class CommandGraphRoot(CommandGraphNode):
    """The root node of the command graph

    Contains all of the elements connected to the root of the command graph.
    """

    @property
    def selector(self) -> None:
        """The selector for the current node"""
        return None

    @property
    def selectors(self) -> list[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        return []

    @property
    def parent(self) -> None:
        """The parent of the current node"""
        return None

    @property
    def children(self) -> list[str]:
        """All of the child elements in the root of the command graph"""
        return ["bar", "group", "layout", "screen", "widget", "window", "core"]


class CommandGraphObject(CommandGraphNode, metaclass=abc.ABCMeta):
    """An object in the command graph that contains a collection of objects"""

    def __init__(self, selector: str | int | None, parent: CommandGraphNode) -> None:
        """A container object in the command graph

        Parameters
        ----------
        selector: str | None
            The name of the selected element within the command graph.  If not
            given, corresponds to the default selection of this type of object.
        parent: CommandGraphNode
            The container object that this object is the child of.
        """
        self._selector = selector
        self._parent = parent

    @property
    def selector(self) -> str | int | None:
        """The selector for the current node"""
        return self._selector

    @property
    def selectors(self) -> list[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        selectors = self.parent.selectors + [(self.object_type, self.selector)]
        return selectors

    @property
    def parent(self) -> CommandGraphNode:
        """The parent of the current node"""
        return self._parent

    @property
    @abc.abstractmethod
    def object_type(self) -> str:
        """The type of the current container object"""


class _BarGraphNode(CommandGraphObject):
    object_type = "bar"
    children = ["screen", "widget"]


class _GroupGraphNode(CommandGraphObject):
    object_type = "group"
    children = ["layout", "window", "screen"]


class _LayoutGraphNode(CommandGraphObject):
    object_type = "layout"
    children = ["group", "window", "screen"]


class _ScreenGraphNode(CommandGraphObject):
    object_type = "screen"
    children = ["layout", "window", "bar", "widget", "group"]


class _WidgetGraphNode(CommandGraphObject):
    object_type = "widget"
    children = ["bar", "screen"]


class _WindowGraphNode(CommandGraphObject):
    object_type = "window"
    children = ["group", "screen", "layout"]


class _CoreGraphNode(CommandGraphObject):
    object_type = "core"
    children: list[str] = []


_COMMAND_GRAPH_MAP: dict[str, Type[CommandGraphObject]] = {
    "bar": _BarGraphNode,
    "group": _GroupGraphNode,
    "layout": _LayoutGraphNode,
    "widget": _WidgetGraphNode,
    "window": _WindowGraphNode,
    "screen": _ScreenGraphNode,
    "core": _CoreGraphNode,
}


GraphType = Union[CommandGraphNode, CommandGraphCall]
