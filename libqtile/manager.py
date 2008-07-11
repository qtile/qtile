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
        if self.group.screen:
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
    def __init__(self, index, x, y, width, height, group):
        self.index, self.x, self.y = index, x, y
        self.width, self.height = width, height
        self.setGroup(group)

    def setGroup(self, g):
        if self.group and self.group != g:
            self.group.hide()
        self.group = g
        self.group.toScreen(self)


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

    def toScreen(self, screen):
        if self.screen:
            self.screen.group = None
        self.screen = screen
        self.layout()

    def hide(self):
        self.screen = None
        for i in self.clients:
            i.hide()

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
            layout = self.layout.name,
            screen = self.screen.index if self.screen else None
        )


class Client:
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.group = None
        window.change_attributes(event_mask=self._windowMask)

    @property
    def name(self):
        try:
            return self.window.get_wm_name()
        except Xlib.error.BadWindow:
            return "<nonexistent>"

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        self.window.change_attributes(
            event_mask=self._windowMask&(~X.StructureNotifyMask)
        )
        self.window.unmap()
        self.window.change_attributes(event_mask=self._windowMask)

    def place(self, x, y, width, height):
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height
        )
        self.window.map()

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
    debug = False
    def __init__(self, display, fname):
        self.display = Xlib.display.Display(display)
        self.fname = fname
        defaultScreen = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = defaultScreen.root

        self.groups = []
        self.groupMap = {}
        for i in self._groupConf:
            g = Group(i, self._layoutConf)
            self.groups.append(g)
            self.groupMap[g.name] = g

        self.screens = []
        if self.display.has_extension("XINERAMA"):
            for i, s in enumerate(self.display.xinerama_query_screens().screens):
                scr = Screen(
                        i,
                        s["x"],
                        s["y"],
                        s["width"],
                        s["height"],
                        self.groups[i]
                    )
                self.screens.append(scr)
        else:
            s = Screen(
                    0, 0, 0,
                    defaultScreen.width_in_pixels,
                    defaultScreen.height_in_pixels,
                    self.groups[0]
                )
            self.screens.append(s)

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
            X.DestroyNotify:    self.destroyNotify,
            X.UnmapNotify:      self.unmapNotify,
            X.EnterNotify:      self.enterNotify,
            X.MappingNotify:    self.mappingNotify,

            X.CreateNotify:     nop,
            # DWM catches this for changes to the root window, and updates
            # screen geometry...
            X.ConfigureNotify:  nop,
            # DWM handles this to help "broken focusing clients".
            X.FocusIn:          nop,
            X.MapNotify:        nop,
            X.LeaveNotify:      nop,
            X.FocusOut:         nop,
        }

    @property
    def currentScreen(self):
        v = self.root.query_pointer()
        for i in self.screens:
            if (v.win_x < i.x + i.width) and (v.win_y < i.y + i.height):
                return i
        return self.screens[0]

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
                    if self.debug:
                        print >> sys.stderr, "Handling:", e
                    h(e)
                else:
                    print >> "Unknown:", sys.stderr, e

    def mappingNotify(self, e):
        self.display.refresh_keyboard_mapping(e)
        # FIXME: Grab our keybindings here

    def enterNotify(self, e):
        c = self.clientMap.get(e.window)
        self.currentScreen.group.focus(c)

    def mapRequest(self, e):
        c = Client(e.window, self)
        self.clientMap[e.window] = c
        self.currentScreen.group.add(c)

    def unmanage(self, window):
        c = self.clientMap.get(window)
        if c:
            c.group.delete(c)
            del self.clientMap[window]

    def destroyNotify(self, e):
        self.unmanage(e.window)

    def unmapNotify(self, e):
        # Ignore SubstructureNotify unmap events
        if  (e.event != e.window) and e.send_event == False:
            return
        self.unmanage(e.window)

    _ignoreErrors = set([
        Xlib.error.BadWindow,
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
        self.currentScreen.group.focusNext()

    def cmd_focusprevious(self):
        self.currentScreen.group.focusPrevious()

    def cmd_screencount(self):
        return len(self.screens)

    def cmd_pullgroup(self, group, screen=None):
        if not screen:
            screen = self.currentScreen
        group = self.groupMap.get(group)
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
