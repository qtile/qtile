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

from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from libqtile.command_client import InteractiveCommandClient
from libqtile.command_graph import (
    CommandGraphCall,
    CommandGraphNode,
    SelectorType,
)
from libqtile.command_interface import CommandInterface


class LazyCall:
    def __init__(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> None:
        """The lazily evaluated command graph call

        Parameters
        ----------
        call : CommandGraphCall
            The call that is made
        args : Tuple
            The args passed to the call when it is evaluated.
        kwargs : Dict
            The kwargs passed to the call when it is evaluated.
        """
        self._call = call
        self._args = args
        self._kwargs = kwargs

        self._layouts = set()  # type: Set[str]
        self._when_floating = True

    @property
    def selectors(self) -> List[SelectorType]:
        """The selectors for the given call"""
        return self._call.selectors

    @property
    def name(self) -> str:
        """The name of the given call"""
        return self._call.name

    @property
    def args(self) -> Tuple:
        """The args to the given call"""
        return self._args

    @property
    def kwargs(self) -> Dict:
        """The kwargs to the given call"""
        return self._kwargs

    def when(self, layout: Optional[Union[Iterable[str], str]] = None,
             when_floating: bool = True) -> 'LazyCall':
        """Enable call only for given layout(s) and floating state

        Parameters
        ----------
        layout : str, Iterable[str], or None
            Restrict call to given layout names. If None, enable call
            for all layouts.
            Can be a single name, a string of comma-separated names, or any
            iterable yielding layout names.
        when_floating : bool
            Enable call when the current window is floating.
        """
        if layout is not None:
            if isinstance(layout, str):
                self._layouts = set(l.strip() for l in layout.split(","))
            else:
                self._layouts = set(layout)

        self._when_floating = when_floating
        return self

    def check(self, q) -> bool:
        cur_win_floating = q.current_window and q.current_window.floating

        if cur_win_floating and not self._when_floating:
            return False

        if self._layouts and q.current_layout.name not in self._layouts:
            return False

        return True


class LazyCommandInterface(CommandInterface):
    """A lazy loading command object

    Allows all commands and items to be resolved at run time, and returns
    lazily evaluated commands.
    """

    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> LazyCall:
        """Lazily evaluate the given call"""
        return LazyCall(call, args, kwargs)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Lazily resolve the given command"""
        return True

    def has_item(self, node: CommandGraphNode, object_type: str, item: Union[str, int]) -> bool:
        """Lazily resolve the given item"""
        return True


lazy = InteractiveCommandClient(LazyCommandInterface())
