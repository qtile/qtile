import inspect, subprocess, sys
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
            self.qtile.log.add("%s(%s, %s)"%(name, args, kwargs))
            return cmd(self.qtile, *args, **kwargs)
        else:
            self.qtile.log.add("Unknown command"%name)
            return "Unknown command: %s"%name
        if self.qtile._testing:
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

    @staticmethod
    def cmd_status(q):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    @staticmethod
    def cmd_to_screen(q, n):
        """
            Warp to screen n.
        """
        return q.toScreen(n)

    @staticmethod
    def cmd_current_screen(q):
        """
            Return current screen number.
        """
        return q.screens.index(q.currentScreen)

    @staticmethod
    def cmd_clientcount(q):
        """
            Return number of clients in all groups.
        """
        return len(q.clientMap)

    @staticmethod
    def cmd_groupinfo(q, name):
        """
            Return group information.
        """
        for i in q.groups:
            if i.name == name:
                return i.info()
        else:
            return None

    @staticmethod
    def cmd_screencount(q):
        return len(q.screens)

    @staticmethod
    def cmd_pullgroup(q, group, screen=None):
        if not screen:
            screen = q.currentScreen
        group = q.groupMap.get(group)
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

    @staticmethod
    def cmd_simulate_keypress(q, modifiers, key):
        """
            Simulates a keypress on the focused window.
        """
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            return "Unknown key: %s"%key
        keycode = q.display.keysym_to_keycode(keysym)
        try:
            mask = utils.translateMasks(modifiers)
        except manager.QTileError, v:
            return str(v)
        if q.currentScreen.group.currentClient:
            win = q.currentScreen.group.currentClient.window
        else:
            win = q.root
        e = event.KeyPress(
                type = X.KeyPress,
                state = mask,
                detail = keycode,

                root = q.root,
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
        q.display.sync()

    @staticmethod
    def cmd_screencount(q):
        return len(q.screens)

    @staticmethod
    def cmd_spawn(q, cmd):
        """
            Run cmd in a shell. Returns the process return code.
        """
        try:
            subprocess.Popen([cmd], shell=True)
        except Exception, v:
            print type(v), v

    @staticmethod
    def cmd_kill(q):
        """
            Kill the window that currently has focus.
        """
        client = q.currentScreen.group.currentClient
        if client:
            client.kill()

    @staticmethod
    def cmd_sync(q):
        q.display.sync()

    @staticmethod
    def cmd_restart(q):
        #q.display.sync()
        pass

    @staticmethod
    def cmd_report(q, msg="None", path="~/qtile_crashreport"):
        q.writeReport(msg, path)


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
