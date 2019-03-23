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

import abc
from typing import Dict, List, Optional, Tuple, Type  # noqa: F401

SelectorType = Tuple[str, Optional[str]]


def _format_selectors(selectors: List[SelectorType]) -> str:
    """Build the path to the selected command graph node"""
    path_elements = []
    for name, selector in selectors:
        if selector:
            path_elements.append("{}[{}]".format(name, selector))
        else:
            path_elements.append(name)
    return ".".join(path_elements)


class CommandGraphCall:
    def __init__(self,
                 selectors: List[SelectorType],
                 name: str,
                 *args,
                 **kwargs) -> None:
        """A command graph call that has been fully resolved"""
        self.selectors = selectors
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def check(self, qtile) -> bool:
        """Check if the command should be called

        By default, call all commands.  Call can be wrapped to provide
        additional granularity and selection ability.
        """
        return True


class _CommandGraphNode(metaclass=abc.ABCMeta):
    """An abstract node in the command graph"""

    @property
    @abc.abstractmethod
    def path(self) -> str:
        """The path to the current command graph node"""
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def parent(self) -> Optional["CommandGraphContainer"]:
        """The parent of the current node"""
        pass  # pragma: no cover


class CommandGraphContainer(_CommandGraphNode, metaclass=abc.ABCMeta):
    """A container node in the command graph structure

    A command graph node which can contain other elements that it can link to.
    May also have commands that can be executed on itself.
    """

    @property
    def path(self) -> str:
        """The path to the current command graph node"""
        return _format_selectors(self.selectors)

    @property
    @abc.abstractmethod
    def selector(self) -> Optional[str]:
        """The selector for the current node"""
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def selectors(self) -> List[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def children(self) -> List[str]:
        """The child objects that are contained within this object"""
        pass  # pragma: no cover

    @abc.abstractmethod
    def __getitem__(self, name: str) -> "CommandGraphContainer":
        """Select a particular element from within the current container"""
        pass  # pragma: no cover

    def __getattr__(self, name: str) -> "_CommandGraphNode":
        """Get the child element of the current container"""
        if name in self.children:
            return _CommandGraphMap[name](None, self)
        else:
            return Command(name, self)


class CommandGraphRoot(CommandGraphContainer):
    """The root node of the command graph

    Contains all of the elements connected to the root of the command graph.
    """

    @property
    def selector(self) -> None:
        """The selector for the current node"""
        return None

    @property
    def selectors(self) -> List[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        return []

    @property
    def parent(self) -> None:
        """The parent of the current node"""
        return None

    @property
    def children(self) -> List[str]:
        """All of the child elements in the root of the command graph"""
        return ["bar", "group", "layout", "screen", "widget", "window"]

    def __getitem__(self, select: str):
        raise KeyError("No items in command root: {}".format(select))


class Command(_CommandGraphNode):
    def __init__(self, name: str, parent: CommandGraphContainer):
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
    def parent(self) -> CommandGraphContainer:
        return self._parent

    def __call__(self, *args, **kwargs) -> CommandGraphCall:
        """Determine the command invokation

        Parameters
        ----------
        args:
            The args to be passed into the call.
        kwargs
            The keyword args to be passed into the call.

        Returns
        -------
        CommandGraphCall
            The call that is being invoked in the command graph.
        """
        selectors = self._parent.selectors
        return CommandGraphCall(selectors, self._name, args, kwargs)

    @property
    def path(self) -> str:
        """The path to the current command graph node"""
        parent_path = self._parent.path
        if parent_path:
            return "{}.{}".format(parent_path, self._name)
        else:
            return self._name


class _CommandGraphObject(CommandGraphContainer, metaclass=abc.ABCMeta):
    def __init__(self, selector: Optional[str], parent: CommandGraphContainer):
        """A container object in the command graph

        Parameters
        ----------
        selector: Optional[str]
            The name of the selected element within the command graph.  If not
            given, corresponds to the default selection of this type of object.
        parent: CommandGraphContainer
            The container object that this object is the child of.
        """
        self._selector = selector
        self._parent = parent

    @property
    def selector(self) -> Optional[str]:
        """The selector for the current node"""
        return self._selector

    @property
    def selectors(self) -> List[SelectorType]:
        """The selectors resolving the location of the node in the command graph"""
        selectors = self.parent.selectors + [(self._object_type, self.selector)]
        return selectors

    @property
    def parent(self) -> CommandGraphContainer:
        """The parent of the current node"""
        return self._parent

    @property
    @abc.abstractmethod
    def _object_type(self) -> str:
        """The type of the current container object"""
        pass  # pragma: no cover

    def __getitem__(self, selection: str) -> "CommandGraphContainer":
        if self.selector is not None:
            raise KeyError("Element {} already selected, cannot make selection: {}".format(
                self.selector, selection
            ))
        return self.__class__(selection, self.parent)


class _BarGraphNode(_CommandGraphObject):
    _object_type = "bar"
    children = ["screen"]


class _GroupGraphNode(_CommandGraphObject):
    _object_type = "group"
    children = ["layout", "window", "screen"]


class _LayoutGraphNode(_CommandGraphObject):
    _object_type = "layout"
    children = ["group", "window", "screen"]


class _ScreenGraphNode(_CommandGraphObject):
    _object_type = "screen"
    children = ["layout", "window", "bar"]


class _WidgetGraphNode(_CommandGraphObject):
    _object_type = "widget"
    children = ["bar", "screen", "group"]


class _WindowGraphNode(_CommandGraphObject):
    _object_type = "window"
    children = ["group", "screen", "layout"]


_CommandGraphMap = {
    "bar": _BarGraphNode,
    "group": _GroupGraphNode,
    "layout": _LayoutGraphNode,
    "widget": _WidgetGraphNode,
    "window": _WindowGraphNode,
    "screen": _ScreenGraphNode,
}  # type: Dict[str, Type[_CommandGraphObject]]
