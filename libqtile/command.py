import inspect
import ipc, utils, manager
from Xlib import XK
from Xlib import X
import Xlib.protocol.event as event

class Client(ipc.Client):
    def __init__(self, fname, command):
        ipc.Client.__init__(self, fname)
        self.command = command

    def __getattr__(self, name):
        funcName = "cmd_" + name
        cmd = getattr(self.command, funcName, None)
        if not cmd:
            raise AttributeError("No such command: %s"%name)
        def callClosure(*args, **kwargs):
            # FIXME: Check arguments here
            # Use inspect.getargspec(v), and craft checks by hand.
            return self.call(name, *args, **kwargs)
        return callClosure


class Command(ipc.Server):
    def __init__(self, fname, qtile):
        ipc.Server.__init__(self, fname, self.call)
        self.qtile = qtile

    def call(self, data):
        name, args, kwargs = data
        cmd = getattr(self, "cmd_" + name, None)
        if cmd:
            return cmd(self.qtile, *args, **kwargs)
        else:
            return "Unknown command: %s"%cmd

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
        if not group:
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
        # facilitate testing...
        qtile.display.sync()
