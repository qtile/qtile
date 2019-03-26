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

from abc import abstractmethod, ABCMeta
from typing import Any, Dict, Tuple

from libqtile.command_graph import CommandGraphCall


class EagerCommandInterface(metaclass=ABCMeta):
    """
    Defines an interface which can be used to eagerly evaluate a given call on
    a command graph.  The implementations of this may use an IPC call to access
    the running qtile instance remotely, or directly access the qtile instance
    from within the same process.
    """

    @abstractmethod
    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> Any:
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
        pass  # pragma: no cover
