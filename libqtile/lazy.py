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
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Dict,
        Iterable,
        List,
        Optional,
        Set,
        Tuple,
        Union,
    )
    from libqtile.config import Match

from libqtile.command.client import InteractiveCommandClient
from libqtile.command.graph import CommandGraphCall, CommandGraphNode, SelectorType
from libqtile.command.interface import CommandInterface


class LazyCall:
    def __init__(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> None:
        """The lazily evaluated command graph call

        Parameters
        ----------
        call: CommandGraphCall
            The call that is made
        args: Tuple
            The args passed to the call when it is evaluated.
        kwargs: Dict
            The kwargs passed to the call when it is evaluated.
        """
        self._call = call
        self._args = args
        self._kwargs = kwargs

        self._focused: Optional[Match] = None
        self._layouts: Set[str] = set()
        self._when_floating = True

    def __call__(self, *args, **kwargs):
        """Convenience method to allow users to pass arguments to
        functions decorated with `@lazy.function`.

            @lazy.function
            def my_function(qtile, pos_arg, keyword_arg=False):
                pass

            ...

            Key(... my_function("Positional argument", keyword_arg=True))

        """
        # We need to return a new object so the arguments are not shared between
        # a single instance of the LazyCall object.
        return LazyCall(self._call, (*self._args, *args), {**self._kwargs, **kwargs})

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

    def when(
        self,
        focused: Optional[Match] = None,
        layout: Optional[Union[Iterable[str], str]] = None,
        when_floating: bool = True,
    ) -> "LazyCall":
        """Enable call only for given layout(s) and floating state

        Parameters
        ----------
        focused: Match or None
            Match criteria to enable call for the current window
        layout: str, Iterable[str], or None
            Restrict call to one or more layouts.
            If None, enable the call for all layouts.
        when_floating: bool
            Enable call when the current window is floating.
        """
        if focused is not None:
            self._focused = focused

        if layout is not None:
            self._layouts = {layout} if isinstance(layout, str) else set(layout)

        self._when_floating = when_floating
        return self

    def check(self, q) -> bool:
        cur_win_floating = q.current_window and q.current_window.floating

        if self._focused and not self._focused.compare(q.current_window):
            return False

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
