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

import inspect
import traceback
import textwrap
import os
import ipc


class CommandError(Exception):
    pass


class CommandException(Exception):
    pass


class _SelectError(Exception):
    def __init__(self, name, sel):
        Exception.__init__(self)
        self.name, self.sel = name, sel


SUCCESS = 0
ERROR = 1
EXCEPTION = 2

SOCKBASE = "qtilesocket.%s"


def formatSelector(lst):
    """
        Takes a list of (name, sel) tuples, and returns a formatted
        selector expression.
    """
    expr = []
    for i in lst:
        if expr:
            expr.append(".")
        expr.append(i[0])
        if i[1] is not None:
            expr.append("[%s]" % repr(i[1]))
    return "".join(expr)


class _Server(ipc.Server):
    def __init__(self, fname, qtile, conf):
        if os.path.exists(fname):
            os.unlink(fname)
        ipc.Server.__init__(self, fname, self.call)
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
        except _SelectError, v:
            e = formatSelector([(v.name, v.sel)])
            s = formatSelector(selectors)
            return ERROR, "No object %s in path '%s'" % (e, s)
        cmd = obj.command(name)
        if not cmd:
            return ERROR, "No such command."
        self.qtile.log.info("Command: %s(%s, %s)" % (name, args, kwargs))
        try:
            return SUCCESS, cmd(*args, **kwargs)
        except CommandError, v:
            return ERROR, v.args[0]
        except Exception, v:
            return EXCEPTION, traceback.format_exc()
        self.qtile.conn.flush()


class _Command:
    def __init__(self, call, selectors, name):
        """
            :command A string command name specification
            :*args Arguments to be passed to the specified command
            :*kwargs Arguments to be passed to the specified command
        """
        self.selectors, self.name = selectors, name
        self.call = call

    def __call__(self, *args, **kwargs):
        return self.call(self.selectors, self.name, *args, **kwargs)


class _CommandTree(object):
    """
        A CommandTree a hierarchical collection of command objects.
        CommandTree objects act as containers, allowing them to be nested. The
        commands themselves appear on the object as callable attributes.
    """
    def __init__(self, call, selectors, myselector, parent):
        self.call = call
        self.selectors = selectors
        self.myselector = myselector
        self.parent = parent

    @property
    def path(self):
        s = self.selectors[:]
        if self.name:
            s += [(self.name, self.myselector)]
        return formatSelector(s)

    def __getitem__(self, select):
        if self.myselector:
            raise KeyError("No such key: %s" % select)
        c = self.__class__(self.call, self.selectors, select, self)
        return c

    def __getattr__(self, name):
        nextSelector = self.selectors[:]
        if self.name:
            nextSelector.append((self.name, self.myselector))
        if name in self._contains:
            return _TreeMap[name](self.call, nextSelector, None, self)
        else:
            return _Command(self.call, nextSelector, name)


class _TLayout(_CommandTree):
    name = "layout"
    _contains = ["group", "window", "screen"]


class _TWidget(_CommandTree):
    name = "widget"
    _contains = ["bar", "screen", "group"]


class _TBar(_CommandTree):
    name = "bar"
    _contains = ["screen"]


class _TWindow(_CommandTree):
    name = "window"
    _contains = ["group", "screen", "layout"]


class _TScreen(_CommandTree):
    name = "screen"
    _contains = ["layout", "window", "bar"]


class _TGroup(_CommandTree):
    name = "group"
    _contains = ["layout", "window", "screen"]


_TreeMap = {
    "layout":   _TLayout,
    "widget":   _TWidget,
    "bar":      _TBar,
    "window":   _TWindow,
    "screen":   _TScreen,
    "group":    _TGroup,
}


class _CommandRoot(_CommandTree):
    name = None
    _contains = ["layout", "widget", "screen", "bar", "window", "group"]

    def __init__(self):
        """
            This method constructs the entire hierarchy of callable commands
            from a conf object.
        """
        _CommandTree.__init__(self, self.call, [], None, None)

    def __getitem__(self, select):
        raise KeyError("No such key: %s" % select)

    def call(self, selectors, name, *args, **kwargs):
        """
            This method is called for issued commands.

                :selectors A list of (name, selector) tuples.
                :name Command name.
        """
        pass


def find_sockfile(display=None):
    """
        Finds the appropriate socket file.
    """
    if not display:
        display = os.environ.get("DISPLAY")
    if not display:
        display = ":0.0"
    if '.' not in display:
        display += '.0'
    cache_directory = os.path.expandvars('$XDG_CACHE_HOME')
    if cache_directory == '$XDG_CACHE_HOME':
        # if variable wasn't set
        cache_directory = os.path.expanduser("~/.cache")
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    return os.path.join(cache_directory, SOCKBASE % display)


class Client(_CommandRoot):
    """
        Exposes a command tree used to communicate with a running instance of
        Qtile.
    """
    def __init__(self, fname=None, conf=None):
        if not fname:
            fname = find_sockfile()
        self.client = ipc.Client(fname)
        _CommandRoot.__init__(self)

    def call(self, selectors, name, *args, **kwargs):
        state, val = self.client.call((selectors, name, args, kwargs))
        if state == SUCCESS:
            return val
        elif state == ERROR:
            raise CommandError(val)
        else:
            raise CommandException(val)


class _Call:
    def __init__(self, selectors, name, *args, **kwargs):
        """
            :command A string command name specification
            :*args Arguments to be passed to the specified command
            :*kwargs Arguments to be passed to the specified command
        """
        self.selectors, self.name = selectors, name
        self.args, self.kwargs = args, kwargs
        # Conditionals
        self.layout = None

    def when(self, layout=None):
        self.layout = layout
        return self

    def check(self, q):
        if self.layout and q.currentLayout.name != self.layout:
            return False
        return True


class _LazyTree(_CommandRoot):
    def call(self, selectors, name, *args, **kwargs):
        return _Call(selectors, name, *args, **kwargs)

lazy = _LazyTree()


class CommandObject(object):
    """
        Base class for objects that expose commands. Each command should be a
        method named cmd_X, where X is the command name.
    """
    def select(self, selectors):
        if not selectors:
            return self
        name, sel = selectors[0]
        selectors = selectors[1:]

        r = self.items(name)
        if (r is None) or\
            (r[1] is None and sel is not None) or\
                (r[1] is not None and sel and sel not in r[1]) or\
                    (r[0] is False and sel is None):
            raise _SelectError(name, sel)

        obj = self._select(name, sel)
        if obj is None:
            raise _SelectError(name, sel)
        return obj.select(selectors)

    def items(self, name):
        """
            Returns a list of contained items for this name.
        """
        ret = self._items(name)
        if ret is None:
            raise CommandError("Unknown item class: %s" % name)
        return ret

    def _items(self, name):
        """
            Return (root, items) tuple for the specified item class, with:

                root: True if this class accepts a "naked" specification
                without an item specification (i.e. "layout"), and False if it
                does not.

                items is a list of contained items, or None if this object is
                not a valid container.

            Return None if name is not a valid item class.
        """
        raise NotImplementedError

    def _select(self, name, sel, selectors):
        """
            Return a selected object, or None if no such object exists.

            This method is called with the following guarantees:
                - name is a valid selector class for this item
                - sel is a valid selector for this item
                - the name, sel tuple is not an "impossible" combination (e.g.
                  a selector is specified when this is not a containment
                  object).
        """
        raise NotImplementedError

    def command(self, name):
        return getattr(self, "cmd_" + name, None)

    def commands(self):
        lst = []
        for i in dir(self):
            if i.startswith("cmd_"):
                lst.append(i[4:])
        return lst

    def cmd_commands(self):
        """
            Returns a list of possible commands for this object.
            Used by __qsh__ for command completion and online help.
        """
        return self.commands()

    def cmd_items(self, name):
        """
            Returns a list of contained items for the specified name. Used by
            __qsh__ to allow navigation of the object graph.
        """
        return self.items(name)

    def docSig(self, name):
        args, varargs, varkw, defaults = inspect.getargspec(self.command(name))
        if args and args[0] == "self":
            args = args[1:]
        return name + inspect.formatargspec(args, varargs, varkw, defaults)

    def docText(self, name):
        return textwrap.dedent(self.command(name).__doc__ or "")

    def doc(self, name):
        spec = self.docSig(name)
        htext = self.docText(name)
        htext = "\n".join([i for i in htext.splitlines()])
        return spec + htext

    def cmd_doc(self, name):
        """
            Returns the documentation for a specified command name. Used by
            __qsh__ to provide online help.
        """
        if name in self.commands():
            return self.doc(name)
        else:
            raise CommandError("No such command: %s" % name)
