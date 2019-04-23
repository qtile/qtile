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

import traceback
import os
import warnings

from . import ipc
from .utils import get_cache_dir
from .log_utils import logger

from libqtile.command_object import SelectError
from libqtile.command_interface import CommandError
from libqtile.command_client import InteractiveCommandClient
from libqtile.lazy import LazyCommandObject


SUCCESS = 0
ERROR = 1
EXCEPTION = 2

SOCKBASE = "qtilesocket.%s"


def format_selectors(lst):
    """
        Takes a list of (name, sel) tuples, and returns a formatted
        selector expression.
    """
    expr = []
    for name, sel in iter(lst):
        if expr:
            expr.append(".")
        expr.append(name)
        if sel is not None:
            expr.append("[%s]" % repr(sel))
    return "".join(expr)


class _Server(ipc.Server):
    def __init__(self, fname, qtile, conf, eventloop):
        if os.path.exists(fname):
            os.unlink(fname)
        ipc.Server.__init__(self, fname, self.call, eventloop)
        self.qtile = qtile
        self.widgets = {}
        for i in conf.screens:
            for j in i.gaps:
                if hasattr(j, "widgets"):
                    for w in j.widgets:
                        if w.name:
                            self.widgets[w.name] = w

    def call(self, data):
        selectors, name, args, kwargs = data
        try:
            obj = self.qtile.select(selectors)
            cmd = obj.command(name)
        except SelectError as v:
            e = format_selectors([(v.name, v.selectors)])
            s = format_selectors(selectors)
            return (ERROR, "No object %s in path '%s'" % (e, s))
        if not cmd:
            return (ERROR, "No such command.")
        logger.debug("Command: %s(%s, %s)", name, args, kwargs)
        try:
            return (SUCCESS, cmd(*args, **kwargs))
        except CommandError as v:
            return (ERROR, v.args[0])
        except Exception:
            return (EXCEPTION, traceback.format_exc())


def find_sockfile(display=None):
    """
        Finds the appropriate socket file.
    """
    display = display or os.environ.get('DISPLAY') or ':0.0'
    if '.' not in display:
        display += '.0'
    cache_directory = get_cache_dir()
    return os.path.join(cache_directory, SOCKBASE % display)


class _LazyTree(InteractiveCommandClient):
    def __getattr__(self, *args, **kwargs):
        warnings.warn("libqtile.command.lazy is deprecated, use libqtile.lazy.lazy", DeprecationWarning)
        return super().__getattr__(*args, **kwargs)


lazy = _LazyTree(LazyCommandObject())
