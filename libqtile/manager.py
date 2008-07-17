import sys, operator
import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X, XK, Xatom
import Xlib.protocol.event as event
import command, utils

class QTileError(Exception): pass


class SkipCommand(Exception): pass


class Command:
    def __init__(self, command, *args, **kwargs):
        self.command, self.args, self.kwargs = command, args, kwargs


class Key:
    def __init__(self, modifiers, key, *commands):
        """
            If multiple commands are specified, they are tried in sequence
            until one does not raise SkipCommand.
        """
        self.modifiers, self.key, self.commands = modifiers, key, commands
        self.keysym = XK.string_to_keysym(key)
        if self.keysym == 0:
            raise QTileError("Unknown key: %s"%key)
        self.modmask = utils.translateMasks(self.modifiers)
    
    def __repr__(self):
        return "Key(%s, %s)"%(self.modifiers, self.key)


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


class Group(list):
    def __init__(self, name, layouts, qtile):
        list.__init__(self)
        self.name, self.qtile = name, qtile
        self.screen = None
        self.layouts = [i.clone(self) for i in layouts]
        self.currentLayout = 0
        self.currentClient = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    def layoutAll(self):
        self.disableMask(X.EnterWindowMask)
        if self.screen and len(self):
            for i in self:
                self.layout.configure(i)
            if self.currentClient:
                self.currentClient.focus()
        self.resetMask()

    def toScreen(self, screen):
        if self.screen:
            self.screen.group = None
        self.screen = screen
        self.layoutAll()

    def hide(self):
        self.screen = None
        for i in self:
            i.hide()

    def focusNext(self):
        idx = (self.index(self.currentClient) + 1) % len(self)
        self.focus(self[idx])

    def focusPrevious(self):
        idx = (self.index(self.currentClient) - 1) % len(self)
        self.focus(self[idx])

    def disableMask(self, mask):
        for i in self:
            i.disableMask(mask)

    def resetMask(self):
        for i in self:
            i.resetMask()

    def focus(self, client):
        if not client:
            self.currentClient = None
        elif self.currentClient != client:
            self.currentClient = client
        self.layoutAll()

    def info(self):
        return dict(
            name = self.name,
            focus = self.currentClient.name if self.currentClient else None,
            clients = [i.name for i in self],
            layout = self.layout.name,
            screen = self.screen.index if self.screen else None
        )

    # List-like operations
    def add(self, client):
        if self.currentClient:
            offset = self.index(self.currentClient)
        else:
            offset = 0
        self.insert(offset, client)
        client.group = self
        for i in self.layouts:
            i.add(client)
        client.window.map()
        self.focus(client)

    def remove(self, client):
        if self.currentClient is client:
            if len(self) > 1:
                self.focusNext()
            else:
                self.focus(None)
        list.remove(self, client)
        client.group = None
        for i in self.layouts:
            i.remove(client)
        self.layoutAll()


class Client:
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.group = None
        self.hidden = True
        window.change_attributes(event_mask=self._windowMask)

    @property
    def name(self):
        try:
            return self.window.get_wm_name()
        except Xlib.error.BadWindow:
            return "<nonexistent>"

    def kill(self):
        if self.hasProtocol("WM_DELETE_WINDOW"):
            e = event.ClientMessage(
                    window = self.window,
                    client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
                    data = [
                        # Use 32-bit format:
                        32,
                        # Must be exactly 20 bytes long:
                        [
                            self.qtile.display.intern_atom("WM_DELETE"),
                            X.CurrentTime,
                            0,
                            0,
                            0
                        ]
                    ]
            )
            self.window.send_event(e)
        else:
            self.window.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        self.disableMask(X.StructureNotifyMask)
        self.window.unmap()
        self.resetMask()
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.hidden = False

    def disableMask(self, mask):
        self.window.change_attributes(
            event_mask=self._windowMask&(~mask)
        )

    def resetMask(self):
        self.window.change_attributes(
            event_mask=self._windowMask
        )

    def place(self, x, y, width, height):
        """
            Places the window at the specified location with the given size.
        """
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def focus(self):
        if not self.hidden:
            self.window.set_input_focus(
                X.RevertToPointerRoot,
                X.CurrentTime
            )
            self.window.configure(
                stack_mode = X.Above
            )

    def hasProtocol(self, name):
        s = set()
        d = self.qtile.display
        for i in self.window.get_wm_protocols():
            s.add(d.get_atom_name(i))
        return name in s

    def __repr__(self):
        return "Client(%s)"%self.name


class QTile:
    testing = False
    debug = False
    _exit = False
    def __init__(self, config, display, fname):
        self.display = Xlib.display.Display(display)
        self.config, self.fname = config, fname
        defaultScreen = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = defaultScreen.root

        self.groups = []
        self.groupMap = {}
        for i in self.config.groups:
            g = Group(i, self.config.layouts, self)
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

        self.display.set_error_handler(self.errorHandler)
        self.root.change_attributes(
            event_mask = X.SubstructureNotifyMask |\
                         X.SubstructureRedirectMask |\
                         X.EnterWindowMask |\
                         X.LeaveWindowMask |\
                         X.StructureNotifyMask
        )
        self.display.sync()
        # Another WM is running...
        if self._exit:
            sys.exit(1)

        self.server = command.Server(self.fname, self, config)

        self.handlers = {
            X.MapRequest:           self.mapRequest,
            X.DestroyNotify:        self.destroyNotify,
            X.UnmapNotify:          self.unmapNotify,
            X.EnterNotify:          self.enterNotify,
            X.MappingNotify:        self.mappingNotify,
            X.KeyPress:             self.keyPress,
            X.ConfigureRequest:     self.configureRequest,
            X.PropertyNotify:       self.propertyNotify,
        }
        self.ignoreEvents = set([
            X.KeyRelease,
            X.ReparentNotify,
            X.CreateNotify,
            # DWM catches this for changes to the root window, and updates
            # screen geometry...
            X.ConfigureNotify,
            # DWM handles this to help "broken focusing clients".
            X.MapNotify,
            X.LeaveNotify,
            X.FocusOut,
            X.FocusIn,
        ])
        self.keyMap = {}
        for i in self.config.keys:
            self.keyMap[(i.keysym, i.modmask)] = i
        self.grabKeys()
        self.scan()

    @property
    def currentLayout(self):
        return self.currentGroup.layout

    @property
    def currentGroup(self):
        return self.currentScreen.group

    @property
    def currentFocus(self):
        return self.currentScreen.group.currentClient

    @property
    def currentScreen(self):
        v = self.root.query_pointer()
        for i in self.screens:
            if (v.win_x < i.x + i.width) and (v.win_y < i.y + i.height):
                return i
        return self.screens[0]

    def scan(self):
        r = self.root.query_tree()
        for i in r.children:
            self.manage(i)

    def unmanage(self, window):
        c = self.clientMap.get(window)
        if c:
            c.group.remove(c)
            del self.clientMap[window]

    def manage(self, w):
        c = Client(w, self)
        self.clientMap[w] = c
        self.currentScreen.group.add(c)

    def grabKeys(self):
        self.root.ungrab_key(X.AnyKey, X.AnyModifier)
        for i in self.keyMap.values():
            code = self.display.keysym_to_keycode(i.keysym)
            self.root.grab_key(
                code,
                i.modmask,
                True,
                X.GrabModeAsync,
                X.GrabModeAsync
            )

    def loop(self):
        while 1:
            if self._exit:
                sys.exit(1)
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
                elif e.type in self.ignoreEvents:
                    pass
                else:
                    print >> sys.stderr, "Unknown:", e

    def keyPress(self, e):
        keysym =  self.display.keycode_to_keysym(e.detail, 0)
        k = self.keyMap.get((keysym, e.state))
        if not k:
            print >> sys.stderr, "Ignoring unknown keysym: %s"%keysym
            return
        for i in k.commands:
            try:
                ret = self.server.call((i.command, i.args, i.kwargs))
                break
            except SkipCommand:
                pass
        if ret:
            print >> sys.stderr, "KB command %s: %s"%(i.command, ret)

    def configureRequest(self, e):
        c = self.clientMap.get(e.window)
        if c and c.group.screen:
            c.group.layout.configure(c)
        else:
            # It's not managed, or not mapped, so we just obey it.
            args = {}
            if e.value_mask & X.CWX:
                args["x"] = e.x
            if e.value_mask & X.CWY:
                args["y"] = e.y
            if e.value_mask & X.CWHeight:
                args["height"] = e.height
            if e.value_mask & X.CWWidth:
                args["width"] = e.width
            if e.value_mask & X.CWBorderWidth:
                args["border_width"] = e.border_width
            e.window.configure(
                **args
            )

    def propertyNotify(self, e):
        c = self.clientMap.get(e.window)
        if c:
            if e.atom == Xatom.WM_TRANSIENT_FOR:
                print >> sys.stderr, "transient"
            elif e.atom == Xatom.WM_HINTS:
                print >> sys.stderr, "hints"
            elif e.atom == Xatom.WM_NORMAL_HINTS:
                print >> sys.stderr, "normal_hints"
            elif e.atom == Xatom.WM_NAME:
                print >> sys.stderr, "name"
            else:
                print >> sys.stderr, e

    def mappingNotify(self, e):
        self.display.refresh_keyboard_mapping(e)
        if e.request == X.MappingKeyboard:
            self.grabKeys()

    def enterNotify(self, e):
        c = self.clientMap.get(e.window)
        if c:
            self.currentScreen.group.focus(c)

    def mapRequest(self, e):
        self.manage(e.window)

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
        if e.__class__ in self._ignoreErrors:
            return
        if e.__class__ == Xlib.error.BadAccess:
            print >> sys.stderr, "Access denied: Another window manager running?"
        else:
            print >> sys.stderr, "Error:", (e, v)
        self._exit = True

