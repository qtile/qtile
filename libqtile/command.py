import inspect, UserDict
import ipc

class _Server(ipc.Server):
    def __init__(self, fname, qtile, config):
        ipc.Server.__init__(self, fname, self.call)
        self.qtile, self.commands = qtile, config.commands()

    def call(self, data):
        name, args, kwargs = data
        cmd = self.commands.get(name)
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


class Commands(UserDict.DictMixin):
    """
        A convenience class for collecting together sets of commands. Command
        collections should inherit from this class, and each command should be
        a method named cmd_X, where X is the command name. The class emulates a
        dictionary exposing the commands.
    """
    def __getitem__(self, itm):
        cmd = getattr(self, "cmd_" + itm, None)
        if not cmd:
            raise KeyError, "No such key: %s"%itm
        return cmd

    def __setitem__(self, itm, value):
        setattr(self, "cmd_" + itm, value)

    def keys(self):
        lst = []
        for i in dir(self):
            if i.startswith("cmd_"):
                lst.append(i[4:])
        return lst

    def __repr__(self):
        return "%s()"%self.__class__.__name__


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
