import sys
import Xlib
import Xlib.protocol.event as event
import Xlib.ext.xinerama as xinerama
import Xlib.X as X
import ipc

class CommandError(Exception): pass


class Screen:
    def __init__(self, x, y, width, height, group):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.group = group


class Group:
    def __init__(self, name):
        self.name = name
        self.clients = []

    def add(self, client):
        self.clients.append(client)


class Client:
    def __init__(self, window):
        self.window = window
        window.change_attributes(
            event_mask = X.StructureNotifyMask |\
                         X.PropertyChangeMask |\
                         X.EnterWindowMask |\
                         X.FocusChangeMask
        )


class QTile:
    _groupConf = ["a", "b", "c", "d"]
    def __init__(self, display, fname):
        self.display = Xlib.display.Display(display)
        self.fname = fname
        scrn = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = scrn.root

        self.groups = []
        for i in self._groupConf:
            self.groups.append(Group(i))

        self.screens = []
        if self.display.has_extension("XINERAMA"):
            for i, s in enumerate(self.display.xinerama_query_screens().screens):
                self.screens.append(
                    Screen(
                        s["x"],
                        s["y"],
                        s["width"],
                        s["height"],
                        self.groups[i]
                    )

                )
        else:
            self.screens.append(
                Screen(
                    0,
                    0,
                    scrn.width_in_pixels,
                    scrn.height_in_pixels,
                    self.groups[0]
                )
            )
        self.currentScreen = self.screens[0]

        self.root.change_attributes(
            event_mask = X.SubstructureNotifyMask |\
                         X.SubstructureRedirectMask |\
                         X.EnterWindowMask |\
                         X.LeaveWindowMask |\
                         X.StructureNotifyMask
        )
        self.display.set_error_handler(self.errorHandler)
        self.server = ipc.Server(self.fname, self.commandHandler)

    def loop(self):
        while 1:
            self.server.receive()
            n = self.display.pending_events()
            while n > 0:
                n -= 1
                e = self.display.next_event()
                if e.type == X.MapRequest:
                    self.mapRequest(e)
                elif e.type == X.CreateNotify:
                    pass
                else:
                    print >> sys.stderr, e

    def mapRequest(self, e):
        self.currentScreen.group.add(
            Client(e.window)
        )

    def errorHandler(self, *args, **kwargs):
        print >> sys.stderr, "Error:", args, kwargs

    def commandHandler(self, data):
        path, args, kwargs = data
        parts = path.split(".")

        obj = self
        funcName = parts[0]
        cmd = getattr(obj, "cmd_" + funcName, None)
        if cmd:
            return cmd(*args, **kwargs)
        else:
            return "Unknown command: %s"%cmd

    def cmd_status(self):
        return "OK"

    def cmd_clientmap(self):
        groups = {}
        for i in self.groups:
            clst = []
            for c in i.clients:
                clst.append(c.window.get_wm_name())
            groups[i.name] = clst
        return groups
