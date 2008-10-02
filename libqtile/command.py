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

import inspect, UserDict, traceback, textwrap, os, inspect
import ipc, config, manager

class CommandError(Exception): pass
class CommandException(Exception): pass

SUCCESS = 0
ERROR = 1
EXCEPTION = 2

SOCKBASE = ".qtilesocket.%s"

class _Server(ipc.Server):
    def __init__(self, fname, qtile, conf):
        if os.path.exists(fname):
            os.unlink(fname)
        ipc.Server.__init__(self, fname, self.call)
        self.qtile = qtile
        self.baseCmds = manager._BaseCommands(qtile)

        self.widgets = {}
        for i in conf.screens:
            for j in i.gaps:
                if hasattr(j, "widgets"):
                    for w in j.widgets:
                        if w.name:
                            self.widgets[w.name] = w

    def call(self, data):
        klass, selector, name, args, kwargs = data
        cmd = None
        if klass == "base":
            cmd = self.baseCmds.command(name)
        elif klass == "layout":
            if not selector:
                cmd = self.qtile.currentLayout.command(name)
            else:
                if selector[0]:
                    pass
        elif klass == "widget":
            if selector in self.widgets:
                cmd = self.widgets[selector].command(name)
        if cmd:
            self.qtile.log.add("Command: %s(%s, %s)"%(name, args, kwargs))
            try:
                return SUCCESS, cmd(*args, **kwargs)
            except CommandError, v:
                return ERROR, v.message
            except Exception, v:
                return EXCEPTION, traceback.format_exc()
        else:
            self.qtile.log.add("Unknown command %s"%name)
            return ERROR, "Unknown command: %s"%name
        if self.qtile._testing:
            self.qtile.display.sync()


class Call:
    def __init__(self, command, *args, **kwargs):
        """
            :command A string command name specification
            :*args Arguments to be passed to the specified command
            :*kwargs Arguments to be passed to the specified command
        """
        self.command, self.args, self.kwargs = command, args, kwargs
        # Conditionals
        self.layout = None

    def when(self, layout=None):
        self.layout = layout
        return self

    def check(self, q):
        if self.layout and q.currentLayout.name != self.layout:
            return False
        return True


class _CommandTree(object):
    """
        A CommandTree a hierarchical collection of command objects.
        CommandTree objects act as containers, allowing them to be nested. The
        commands themselves appear on the object as callable attributes.
    """
    def __init__(self, objs, klass, selector, call = None):
        self.objs, self.klass, self.selector = objs, klass, selector
        if call:
            self.call = call
        self.items = {}

    def __getitem__(self, name):
        return self.items[name]

    def __setitem__(self, name, itm):
        self.items[name] = itm

    def __getattr__(self, name):
        funcName = "cmd_" + name
        cmd = None
        for i in self.objs:
            cmd = getattr(i, funcName, None)
            if cmd:
                break
        if not cmd:
            raise AttributeError("No such command: %s"%name)
        def callClosure(*args, **kwargs):
            return self.call(self.klass, self.selector, name, *args, **kwargs)
        return callClosure

    def call(self, klass, selector, name, *args, **kwargs):
        """
            This method is called for issued commands.
                
                :klass  "widget", "layout" or "base".
                :selector A string  name for widgets, or a (group, offset)
                tuple for layouts. Here, "offset" can be None, indicating the
                current layout for the specified group.
                :name Command name.
        """
        pass


class _CommandRoot(_CommandTree):
    def __init__(self, conf):
        """
            This method constructs the entire hierarchy of callable commands
            from a conf object.
        """
        _CommandTree.__init__(self, [manager._BaseCommands(None)], "base", None)
        self.layout = _CommandTree(conf.layouts, "layout", None, self.call)
        for i in conf.groups:
            g = _CommandTree(conf.layouts, "layout", (i, None), self.call)
            for x, l in enumerate(conf.layouts):
                g[x] = _CommandTree([l], "layout", (i, x), self.call)
            self.layout[i] = g
        self.widget = _CommandTree([], None, None, None)
        for i in conf.screens:
            for j in i.gaps:
                if hasattr(j, "widgets"):
                    for w in j.widgets:
                        if w.name:
                            self.widget[w.name] = _CommandTree([w], "widget", w.name, self.call)


class Client(_CommandRoot):
    def __init__(self, fname=None, conf=None):
        if not fname:
            d = os.environ.get("DISPLAY")
            if not d:
                d = ":0.0"
            fname = os.path.join("~", SOCKBASE%d)
            fname = os.path.expanduser(fname)
        self.client = ipc.Client(fname)
        if not conf:
            conf = config.File()
        _CommandRoot.__init__(self, conf)

    def call(self, klass, selector, name, *args, **kwargs):
        # FIXME: Check arguments here
        # Use inspect.getargspec(v), and craft checks by hand.
        state, val = self.client.call((klass, selector, name, args, kwargs))
        if state == SUCCESS:
            return val
        elif state == ERROR:
            raise CommandError(val)
        else:
            raise CommandException(val)


class CommandObject(object):
    """
        A convenience class for collecting together sets of commands. Command
        collections should inherit from this class, and each command should be
        a method named cmd_X, where X is the command name. 
    """
    def command(self, name):
        return getattr(self, "cmd_" + name, None)

    def commands(self):
        lst = []
        for i in dir(self):
            if i.startswith("cmd_"):
                lst.append(i[4:])
        return lst

    def docSig(self, name):
        args, varargs, varkw, defaults = inspect.getargspec(self.command(name))
        if args[0] == "self":
            args = args[1:]
        return name + inspect.formatargspec(args, varargs, varkw, defaults)

    def docText(self, name):
        return textwrap.dedent(self.command(name).__doc__ or "")

    def doc(self, name):
        spec = self.docSig(name)
        htext = self.docText(name)
        htext = "\n".join(["\t" + i for i in htext.splitlines()])
        return spec + htext
