import sys, operator, copy
import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X, XK, Xatom
import Xlib.protocol.event as event
import command, utils

class QTileError(Exception): pass


class SkipCommand(Exception): pass


class Call:
    def __init__(self, command, *args, **kwargs):
        self.command, self.args, self.kwargs = command, args, kwargs


class Key:
    def __init__(self, modifiers, key, *commands):
        self.modifiers, self.key, self.commands = modifiers, key, commands
        self.keysym = XK.string_to_keysym(key)
        if self.keysym == 0:
            raise QTileError("Unknown key: %s"%key)
        self.modmask = utils.translateMasks(self.modifiers)
    
    def __repr__(self):
        return "Key(%s, %s)"%(self.modifiers, self.key)


class _Layout:
    def clone(self, group):
        c = copy.copy(self)
        c.group = group
        return c


class Max(_Layout):
    name = "max"
    def configure(self, c):
        if c == self.group.focusClient:
            c.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
        else:
            c.hide()

    def cmd_max_next(self, qtile, noskip=False):
        pass

    def cmd_max_previous(self, qtile, noskip=False):
        pass


class Stack(_Layout):
    name = "stack"
    def __init__(self, columns=2):
        self.columns = columns

    def configure(self, c):
        if c == self.group.focusClient:
            c.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
        else:
            c.hide()

    def cmd_stack_down(self, qtile, noskip=False):
        pass

    def cmd_stack_up(self, qtile, noskip=False):
        pass

    def cmd_stack_swap(self, qtile, noskip=False):
        pass

    def cmd_stack_move(self, qtile, noskip=False):
        pass


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
        self.layouts = [i.clone(self) for i in layouts]
        self.currentLayout = 0
        self.focusClient = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    def layoutAll(self):
        if self.screen and self.clients:
            for i in self.clients:
                self.layout.configure(i)
            self.focusClient.focus()

    def toScreen(self, screen):
        if self.screen:
            self.screen.group = None
        self.screen = screen
        self.layoutAll()

    def hide(self):
        self.screen = None
        for i in self.clients:
            i.hide()

    def add(self, client):
        if self.focusClient:
            offset = self.clients.index(self.focusClient)
        else:
            offset = 0
        self.clients.insert(offset, client)
        client.group = self
        self.focus(client)

    def remove(self, client):
        if self.focusClient is client:
            if len(self.clients) > 1:
                self.focusNext()
            else:
                self.focus(None)
        self.clients.remove(client)
        client.group = None
        self.layoutAll()

    def focusNext(self):
        idx = (self.clients.index(self.focusClient) + 1) % len(self.clients)
        self.focus(self.clients[idx])

    def focusPrevious(self):
        idx = (self.clients.index(self.focusClient) - 1) % len(self.clients)
        self.focus(self.clients[idx])

    def disableMask(self, mask):
        for i in self.clients:
            i.disableMask(mask)

    def resetMask(self):
        for i in self.clients:
            i.resetMask()

    def focus(self, client):
        if not client:
            self.focusClient = None
        elif self.focusClient != client:
            self.disableMask(X.EnterWindowMask)
            self.focusClient = client
            if self.screen:
                self.layoutAll()
            self.resetMask()

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

    def disableMask(self, mask):
        self.window.change_attributes(
            event_mask=self._windowMask&(~mask)
        )

    def resetMask(self):
        self.window.change_attributes(
            event_mask=self._windowMask
        )

    def place(self, x, y, width, height):
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height,
        )
        self.window.map()

    def focus(self):
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
            g = Group(i, self.config.layouts)
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

        nop = lambda e: None
        self.handlers = {
            X.MapRequest:           self.mapRequest,
            X.DestroyNotify:        self.destroyNotify,
            X.UnmapNotify:          self.unmapNotify,
            X.EnterNotify:          self.enterNotify,
            X.MappingNotify:        self.mappingNotify,
            X.KeyPress:             self.keyPress,
            X.ConfigureRequest:     self.configureRequest,
            X.PropertyNotify:       self.propertyNotify,

            X.KeyRelease:           nop,
            X.ReparentNotify:       nop,
            X.CreateNotify:         nop,
            # DWM catches this for changes to the root window, and updates
            # screen geometry...
            X.ConfigureNotify:      nop,
            # DWM handles this to help "broken focusing clients".
            X.MapNotify:            nop,
            X.LeaveNotify:          nop,
            X.FocusOut:             nop,
            X.FocusIn:              nop,
        }
        self.keyMap = {}
        for i in self.config.keys:
            self.keyMap[(i.keysym, i.modmask)] = i
        self.grabKeys()
        self.scan()

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

    @property
    def currentScreen(self):
        v = self.root.query_pointer()
        for i in self.screens:
            if (v.win_x < i.x + i.width) and (v.win_y < i.y + i.height):
                return i
        return self.screens[0]

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

