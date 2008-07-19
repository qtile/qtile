import inspect, subprocess, sys
import ipc, utils, manager
from Xlib import XK
from Xlib import X
import Xlib.protocol.event as event

class _Server(ipc.Server):
    def __init__(self, fname, qtile, config):
        ipc.Server.__init__(self, fname, self.call)
        self.qtile, self.commands = qtile, config.commands()

    def call(self, data):
        name, args, kwargs = data
        cmd = getattr(self.commands, "cmd_" + name, None)
        if cmd:
            self.qtile.log.add("%s(%s, %s)"%(name, args, kwargs))
            return cmd(self.qtile, *args, **kwargs)
        else:
            self.qtile.log.add("Unknown command"%name)
            return "Unknown command: %s"%name
        if self.qtile._testing:
            self.qtile.display.sync()


class Call:
    def __init__(self, command, *args, **kwargs):
        self.command, self.args, self.kwargs = command, args, kwargs


class Client(ipc.Client):
    def __init__(self, fname, config):
        ipc.Client.__init__(self, fname)
        self.commands = config.commands()

    def __getattr__(self, name):
        funcName = "cmd_" + name
        cmd = getattr(self.commands, funcName, None)
        if not cmd:
            raise AttributeError("No such command: %s"%name)
        def callClosure(*args, **kwargs):
            # FIXME: Check arguments here
            # Use inspect.getargspec(v), and craft checks by hand.
            return self.call(name, *args, **kwargs)
        return callClosure
