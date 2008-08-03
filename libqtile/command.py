import inspect, UserDict, traceback, textwrap, os, inspect
import ipc, config

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
        self.qtile, self.commands = qtile, conf.commands()

    def call(self, data):
        name, args, kwargs = data
        cmd = self.commands.get(name)
        if cmd:
            self.qtile.log.add("Command: %s(%s, %s)"%(name, args, kwargs))
            try:
                return SUCCESS, cmd(self.qtile, *args, **kwargs)
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


class Client(ipc.Client):
    def __init__(self, fname=None, conf=None):
        if not fname:
            d = os.environ.get("DISPLAY")
            if not d:
                d = ":0.0"
            fname = os.path.join("~", SOCKBASE%d)
            fname = os.path.expanduser(fname)
        ipc.Client.__init__(self, fname)
        if not conf:
            conf = config.File()
        self.commands = conf.commands()

    def __getattr__(self, name):
        funcName = "cmd_" + name
        cmd = getattr(self.commands, funcName, None)
        if not cmd:
            raise AttributeError("No such command: %s"%name)
        def callClosure(*args, **kwargs):
            # FIXME: Check arguments here
            # Use inspect.getargspec(v), and craft checks by hand.
            state, val = self.call(name, *args, **kwargs)
            if state == SUCCESS:
                return val
            elif state == ERROR:
                raise CommandError(val)
            else:
                raise CommandException(val)
        return callClosure


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

    def doc(self, name):
        args, varargs, varkw, defaults = inspect.getargspec(self[name])
        if args[0] == "self":
            args = args[1:]
        args = args[1:]
        spec = name + inspect.formatargspec(args, varargs, varkw, defaults)
        htext = textwrap.dedent(self[name].__doc__ or "")
        htext = "\n".join(["\t" + i for i in htext.splitlines()])
        return spec + htext

    def __repr__(self):
        return "%s()"%self.__class__.__name__
