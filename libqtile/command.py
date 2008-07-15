import inspect, subprocess
import ipc, utils, manager
from Xlib import XK
from Xlib import X
import Xlib.protocol.event as event

class Server(ipc.Server):
    def __init__(self, fname, qtile, config):
        ipc.Server.__init__(self, fname, self.call)
        self.qtile, self.commands = qtile, config.commands()

    def call(self, data):
        name, args, kwargs = data
        cmd = getattr(self.commands, "cmd_" + name, None)
        if cmd:
            return cmd(self.qtile, *args, **kwargs)
        else:
            return "Unknown command: %s"%cmd
        if self.qtile.testing:
            self.qtile.display.sync()


class BaseCommand:
    def add(self, obj):
        """
            Adds all cmd_* methods from the specified object.
        """
        for i in dir(obj):
            if i.startswith("cmd_"):
                attr = getattr(obj, i)
                setattr(self, i, attr)

    def cmd_status(self, qtile):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    def cmd_clientcount(self, qtile):
        """
            Return number of clients in all groups.
        """
        return len(qtile.clientMap)

    def cmd_groupinfo(self, qtile, name):
        """
            Return group information.
        """
        for i in qtile.groups:
            if i.name == name:
                return i.info()
        else:
            return None

    def cmd_focusnext(self, qtile):
        qtile.currentScreen.group.focusNext()

    def cmd_focusprevious(self, qtile):
        qtile.currentScreen.group.focusPrevious()

    def cmd_screencount(self, qtile):
        return len(qtile.screens)

    def cmd_pullgroup(self, qtile, group, screen=None):
        if not screen:
            screen = qtile.currentScreen
        group = qtile.groupMap.get(group)
        if group is None:
            return "No such group"
        elif group.screen == screen:
            return
        elif group.screen:
            g = screen.group
            s = group.screen
            s.setGroup(g)
            screen.setGroup(group)
        else:
            screen.setGroup(group)

    def cmd_simulate_keypress(self, qtile, modifiers, key):
        """
            Simulates a keypress on the focused window.
        """
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            return "Unknown key: %s"%key
        keycode = qtile.display.keysym_to_keycode(keysym)
        try:
            mask = utils.translateMasks(modifiers)
        except manager.QTileError, v:
            return str(v)
        if qtile.currentScreen.group.focusClient:
            win = qtile.currentScreen.group.focusClient.window
        else:
            win = qtile.root
        e = event.KeyPress(
                type = X.KeyPress,
                state = mask,
                detail = keycode,

                root = qtile.root,
                window = win,
                child = X.NONE,

                time = X.CurrentTime,
                root_x = 1,
                root_y = 1,
                event_x = 1,
                event_y = 1,
                same_screen = 1,
        )
        win.send_event(e, X.KeyPressMask|X.SubstructureNotifyMask, propagate=True)
        # I guess we could abstract this out into a cmd_sync command to
        qtile.display.sync()

    def cmd_screencount(self, qtile):
        return len(qtile.screens)

    def cmd_spawn(self, qtile, cmd):
        """
            Run cmd in a shell. Returns the process return code.
        """
        try:
            subprocess.Popen([cmd], shell=True)
        except Exception, v:
            print type(v), v

    def cmd_kill(self, qtile):
        """
            Kill the window that currently has focus.
        """
        client = qtile.currentScreen.group.focusClient
        if client:
            client.kill()

    def cmd_sync(self, qtile):
        qtile.display.sync()


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
