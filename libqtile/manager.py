import sys
import Xlib
import Xlib.display
import Xlib.protocol.event as event
import Xlib.ext.xinerama as xinerama
import Xlib.X as X
import ipc

class CommandError(Exception): pass


class Max:
    name = "max"
    def __init__(self, group):
        self.group = group

    def __call__(self):
        for i in self.group.clients:
            i.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
        if self.group.focusClient:
            self.group.focusClient.focus()


class Screen:
    group = None
    def __init__(self, x, y, width, height, group):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.setGroup(group)

    def setGroup(self, g):
        if self.group:
            self.group.screen = None
        self.group = g
        g.screen = self


class Group:
    def __init__(self, name, layouts):
        self.name = name
        self.screen = None
        self.clients = []
        self.layouts = [i(self) for i in layouts]
        self.currentLayout = 0
        self.focusClient = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    def add(self, client):
        self.clients.append(client)
        client.group = self
        self.focus(client)

    def delete(self, client):
        if self.focusClient is client:
            if len(self.clients) > 1:
                self.focusNext()
            else:
                self.focus(None)
        self.clients.remove(client)
        client.group = None
        self.layout()

    def focusNext(self):
        idx = (self.clients.index(self.focusClient) + 1) % len(self.clients)
        self.focus(self.clients[idx])

    def focusPrevious(self):
        idx = (self.clients.index(self.focusClient) - 1) % len(self.clients)
        self.focus(self.clients[idx])

    def focus(self, client):
        if self.focusClient != client:
            self.focusClient = client
            self.layout()

    def info(self):
        return dict(
            name = self.name,
            focus = self.focusClient.name if self.focusClient else None,
            clients = [i.name for i in self.clients],
            layout = self.layout.name
        )


class Client:
    def __init__(self, window):
        self.window = window
        self.group = None
        window.change_attributes(
            event_mask = X.StructureNotifyMask |\
                         X.PropertyChangeMask |\
                         X.EnterWindowMask |\
                         X.FocusChangeMask
        )

    @property
    def name(self):
        try:
            return self.window.get_wm_name()
        except Xlib.error.BadWindow:
            return "<nonexistent>"

    def place(self, x, y, width, height):
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height
        )

    def focus(self):
        self.window.set_input_focus(
            X.RevertToPointerRoot,
            X.CurrentTime
        )

    def __repr__(self):
        return "Client(%s)"%self.name


class QTile:
    _groupConf = ["a", "b", "c", "d"]
    _layoutConf = [Max]
    def __init__(self, display, fname):
        self.display = Xlib.display.Display(display)
        self.fname = fname
        defaultScreen = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = defaultScreen.root

        self.groups = []
        for i in self._groupConf:
            self.groups.append(Group(i, self._layoutConf))

        self.screens = []
        if self.display.has_extension("XINERAMA"):
            for i, s in enumerate(self.display.xinerama_query_screens().screens):
                scr = Screen(
                        s["x"],
                        s["y"],
                        s["width"],
                        s["height"],
                        self.groups[i]
                    )
                self.screens.append(scr)
        else:
            s = Screen(
                    0, 0,
                    defaultScreen.width_in_pixels,
                    defaultScreen.height_in_pixels,
                    self.groups[0]
                )
            self.screens.append(s)

        self.currentScreen = self.screens[0]
        self.clientMap = {}

        self.root.change_attributes(
            event_mask = X.SubstructureNotifyMask |\
                         X.SubstructureRedirectMask |\
                         X.EnterWindowMask |\
                         X.LeaveWindowMask |\
                         X.StructureNotifyMask
        )
        self.display.set_error_handler(self.errorHandler)
        self.server = ipc.Server(self.fname, self.commandHandler)

        nop = lambda e: None
        self.handlers = {
            X.MapRequest:       self.mapRequest,
            X.DestroyNotify:    self.unmanage,
            X.UnmapNotify:      self.unmanage,

            X.CreateNotify:     nop,
            # DWM catches this for changes to the root window, and updates
            # screen geometry...
            X.ConfigureNotify:  nop,
            X.MapNotify:        nop,
            X.LeaveNotify:      nop,
            X.FocusOut:         nop,
        }

    def loop(self):
        while 1:
            self.server.receive()
            try:
                n = self.display.pending_events()
            except Xlib.error.ConnectionClosedError:
                return
            while n > 0:
                n -= 1
                e = self.display.next_event()
                h = self.handlers.get(e.type)
                if h:
                    h(e)
                else:
                    print >> sys.stderr, e

    def mapRequest(self, e):
        c = Client(e.window)
        e.window.map()
        self.clientMap[e.window] = c
        self.currentScreen.group.add(c)

    def unmanage(self, e):
        c = self.clientMap.get(e.window)
        if c:
            c.group.delete(c)
            del self.clientMap[e.window]

    _ignoreErrors = set([
        Xlib.error.BadWindow
    ])
    def errorHandler(self, e, v):
        if e.__class__ not in self._ignoreErrors:
            print >> sys.stderr, "Error:", (e, v)

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
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    def cmd_clientcount(self):
        """
            Return number of clients in all groups.
        """
        return len(self.clientMap)

    def cmd_groupinfo(self, name):
        """
            Return group information.
        """
        for i in self.groups:
            if i.name == name:
                return i.info()
        else:
            return None

    def cmd_focusnext(self):
        return "OK"

    def cmd_focusprevious(self):
        return "OK"
