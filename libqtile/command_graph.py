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


class CommandGraphCall:
    def __init__(self,
                 selectors: List[Tuple[str, Optional[str]]],
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

    @abc.abstractmethod
    def call(self,
             selectors: List[Tuple[str, Optional[str]]],
             name: str,
             *args,
             **kwargs) -> CommandGraphCall:
        """Execute the given call against the selected command"""
        pass

    @abc.abstractmethod
    def __getattr__(self, selection: str) -> "_CommandGraphNode":
        """Navigate within the graph to the new command graph element

        May be navigating to another container node, or to a terminal command
        node.
        """
        pass

    @abc.abstractmethod
    def __getitem__(self, name: str) -> "_CommandGraphNode":
        """Select a particular element from within the current container"""
        pass


class _CommandGraphContainer(_CommandGraphNode, metaclass=abc.ABCMeta):
    """A container node in the command graph structure

    A command graph node which can contain other elements that it can link to.
    May also have commands that can be executed on itself.
    """

    @property
    @abc.abstractmethod
    def children(self) -> List[str]:
        pass

    @property
    @abc.abstractmethod
    def parent(self) -> Optional["_CommandGraphContainer"]:
        pass

    def __getattr__(self, name: str) -> _CommandGraphNode:
        if name in self.children:
            return _CommandGraphMap[name](None, self)
        else:
            return _Command(name, self)


class CommandGraphRoot(_CommandGraphContainer):
    """The root node of the command graph

    Contains all of the elements connected to the root of the command graph.
    """

    @property
    def children(self):
        return ["layout", "widget", "screen", "bar", "window", "group"]

    @property
    def parent(self) -> None:
        return None

    def call(self,
             selectors: List[Tuple[str, Optional[str]]],
             name: str,
             *args,
             **kwargs) -> CommandGraphCall:
        """Return the fully resolved command graph call"""
        return CommandGraphCall(selectors, name, *args, **kwargs)

    def __getitem__(self, select: str):
        raise KeyError("No items in command root: {}".format(select))


class _CommandGraphObject(_CommandGraphContainer, metaclass=abc.ABCMeta):
    def __init__(self, selector: Optional[str], parent: _CommandGraphContainer):
        self._selector = selector
        self._parent = parent

    @property
    @abc.abstractmethod
    def object_type(self) -> str:
        pass

    @property
    def parent(self) -> _CommandGraphContainer:
        return self._parent

    def call(self,
             selectors: List[Tuple[str, Optional[str]]],
             name: str,
             *args,
             **kwargs) -> CommandGraphCall:
        """Perform the given call

        Pass the given call up to the parent node in the command graph to be
        executed.
        """
        selectors = [(self.object_type, self._selector)] + selectors
        return self._parent.call(selectors, name, *args, **kwargs)

    def __getitem__(self, selection: str) -> _CommandGraphNode:
        if self._selector is not None:
            raise KeyError("Element {} already selected, cannot make selection: {}".format(
                self._selector, selection
            ))
        self._selector = selection
        return self


class _Command(_CommandGraphNode):
    def __init__(self, name: str, parent: _CommandGraphNode):
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

    def __call__(self, *args, **kwargs) -> CommandGraphCall:
        """
            :*args Arguments to be passed to the specified command
            :*kwargs Arguments to be passed to the specified command
        """
        return self.call([], self._name, *args, **kwargs)

    def call(self,
             selectors: List[Tuple[str, Optional[str]]],
             name: str,
             *args,
             **kwargs) -> CommandGraphCall:
        return self._parent.call(selectors, name, *args, **kwargs)

    def __getattr__(self, selection: str) -> _CommandGraphNode:
        raise KeyError("Cannot make selection {} on command {}".format(selection, self.name))

    def __getitem__(self, name: str) -> _CommandGraphNode:
        raise ValueError("Cannot get selection {} on command {}".format(name, self.name))


class _BarGraphNode(_CommandGraphObject):
    object_type = "bar"
    children = ["screen"]


class _GroupGraphNode(_CommandGraphObject):
    object_type = "group"
    children = ["layout", "window", "screen"]


class _LayoutGraphNode(_CommandGraphObject):
    object_type = "layout"
    children = ["group", "window", "screen"]


class _ScreenGraphNode(_CommandGraphObject):
    object_type = "screen"
    children = ["layout", "window", "bar"]


class _WidgetGraphNode(_CommandGraphObject):
    object_type = "widget"
    children = ["bar", "screen", "group"]


class _WindowGraphNode(_CommandGraphObject):
    object_type = "window"
    children = ["group", "screen", "layout"]


_CommandGraphMap = {
    "bar": _BarGraphNode,
    "group": _GroupGraphNode,
    "layout": _LayoutGraphNode,
    "widget": _WidgetGraphNode,
    "window": _WindowGraphNode,
    "screen": _ScreenGraphNode,
}  # type: Dict[str, Type[_CommandGraphObject]]
