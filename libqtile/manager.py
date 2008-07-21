import datetime, subprocess, sys, operator, os, traceback
import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X, XK, Xatom
import Xlib.protocol.event as event
import command, utils

class QTileError(Exception): pass


class SkipCommand(Exception): pass


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


class Gap:
    def __init__(self, width):
        self.width = width


class Screen:
    group = None
    def __init__(self, top=None, bottom=None, left=None, right=None):
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right

    def _configure(self, index, x, y, width, height, group):
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)

    @property
    def dx(self):
        return self.x + self.left.width if self.left else 0

    @property
    def dwidth(self):
        val = self.width - self.dx
        if self.right:
            val -= self.right.width
        return val

    @property
    def dy(self):
        return self.y + self.top.width if self.top else 0

    @property
    def dheight(self):
        val = self.height - self.dy
        if self.bottom:
            val -= self.bottom.width
        return val

    def setGroup(self, g):
        if not (self.group is None) and self.group is not g:
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

    def nextLayout(self):
        self.currentLayout = (self.currentLayout + 1)%(len(self.layouts))
        self.layoutAll()

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

    def disableMask(self, mask):
        for i in self:
            i.disableMask(mask)

    def resetMask(self):
        for i in self:
            i.resetMask()

    def focus(self, client):
        if client == self.currentClient:
            return
        if not client:
            self.currentClient = None
        else:
            self.currentClient = client
        self.layout.focus(client)
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


class _Window:
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        window.change_attributes(event_mask=self._windowMask)
        self.x, self.y, self.width, self.height = None, None, None, None

    def info(self):
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            id = str(hex(self.window.id))
        )

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
        self.x, self.y, self.width, self.height = None, None, None, None
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
        self.x, self.y, self.width, self.height = x, y, width, height
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
            self.window.warp_pointer(0, 0)

    def hasProtocol(self, name):
        s = set()
        d = self.qtile.display
        for i in self.window.get_wm_protocols():
            s.add(d.get_atom_name(i))
        return name in s


class Internal(_Window):
    def __repr__(self):
        return "Internal(%s)"%self.name


class Client(_Window):
    group = None
    def __repr__(self):
        return "Client(%s)"%self.name


class Log:
    """
        A circular log.
    """
    def __init__(self, length, outfile):
        self.length, self.outfile = length, outfile
        self.log = []

    def add(self, itm):
        if self.outfile:
            print >> self.outfile, itm
        self.log.append(itm)
        if len(self.log) > self.length:
            self.log.pop(0)

    def write(self, fp, initial):
        for i in self.log:
            print >> fp, initial, i


class QTile:
    debug = False
    _exit = False
    _testing = False

    # Atoms
    atom_qtilewindow = None
    _debugLogLength = 50
    def __init__(self, config, displayName, fname):
        self.display = Xlib.display.Display(displayName)
        self.config, self.fname = config, fname
        self.log = Log(
            self._debugLogLength,
            sys.stderr if self.debug else None
        )
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
                if i+1 > len(config.screens):
                    scr = Screen()
                else:
                    scr = config.screens[i]
                scr._configure(
                    i,
                    s["x"],
                    s["y"],
                    s["width"],
                    s["height"],
                    self.groups[i]
                )
                self.screens.append(scr)
        else:
            if config.screens:
                s = config.screens[0]
            else:
                s = Screen()
            s._configure(
                0, 0, 0,
                defaultScreen.width_in_pixels,
                defaultScreen.height_in_pixels,
                self.groups[0]
            )
            self.screens.append(s)
        self.currentScreen = self.screens[0]

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
        if self._exit:
            print >> sys.stderr, "Access denied: Another window manager running?"
            sys.exit(1)

        self.atom_qtilewindow = self.display.intern_atom("QTILE_WINDOW")

        self.server = command._Server(self.fname, self, config)

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
    def currentClient(self):
        return self.currentScreen.group.currentClient

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
        try:
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
                        self.log.add("Handling: %s"%e)
                        h(e)
                    elif e.type in self.ignoreEvents:
                        pass
                    else:
                        self.log.add("Unknown event: %s"%e)
        except:
            self.writeReport(traceback.format_exc())

    def keyPress(self, e):
        keysym =  self.display.keycode_to_keysym(e.detail, 0)
        k = self.keyMap.get((keysym, e.state))
        if not k:
            print >> sys.stderr, "Ignoring unknown keysym: %s"%keysym
            return
        for i in k.commands:
            if i.check(self):
                status, val = self.server.call((i.command, i.args, i.kwargs))
                break
        else:
            return
        if status in (command.ERROR, command.EXCEPTION):
            s = "KB command error %s: %s"%(i.command, val)
            q.log.add(s)
            print >> sys.stderr, s

    def configureRequest(self, e):
        c = self.clientMap.get(e.window)
        if c and c.group.screen:
            c.group.focus(c)
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
        c = self.clientMap.get(e.window)
        if not c:
            self.manage(e.window)

    def destroyNotify(self, e):
        self.unmanage(e.window)

    def unmapNotify(self, e):
        # Ignore SubstructureNotify unmap events
        if  (e.event != e.window) and e.send_event == False:
            return
        self.unmanage(e.window)

    def toScreen(self, n):
        if len(self.screens) < n-1:
            return
        self.currentScreen = self.screens[n]

    def writeReport(self, m, path="~/qtile_crashreport", _force=False):
        if self._testing and not _force:
            print >> sys.stderr, "Server Error:", m
            return
        p = os.path.expanduser(path)
        f = open(p, "a+")
        print >> f, "*** QTILE REPORT", datetime.datetime.now()
        print >> f, "Message:", m
        print >> f, "Last %s events:"%self.log.length
        self.log.write(f, "\t")
        f.close()

    _ignoreErrors = set([
        Xlib.error.BadWindow,
    ])
    def errorHandler(self, e, v):
        if e.__class__ in self._ignoreErrors:
            return
        if self._testing:
            print >> sys.stderr, "Server Error:", (e, v)
        else:
            self.writeReport((e, v))
        self._exit = True


class _BaseCommands(command.Commands):
    @staticmethod
    def cmd_status(q):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    @staticmethod
    def cmd_to_screen(q, n):
        """
            Warp to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return q.toScreen(n)

    @staticmethod
    def cmd_current_screen(q):
        """
            Return current screen number.
        """
        return q.screens.index(q.currentScreen)

    @staticmethod
    def cmd_clients(q):
        """
            Return number of clients in all groups.
        """
        return [i.info() for i in q.clientMap.values()]

    @staticmethod
    def cmd_nextlayout(q, group=None):
        """
            Switch to the next layout.
        """
        if group:
            group = q.groupMap.get(groupName)
        else:
            group = q.currentGroup
        group.nextLayout()

    @staticmethod
    def cmd_groupinfo(q, name):
        """
            Return group information for a specified group.

            Example:
                
                groupinfo("a")
        """
        for i in q.groups:
            if i.name == name:
                return i.info()
        else:
            return None

    @staticmethod
    def cmd_screens(q):
        """
            Return screen information.
        """
        lst = []
        for i in q.screens:
            lst.append(dict(
                index = i.index,
                group = i.group.name if i.group is not None else None,
                x = i.x,
                y = i.y,
                width = i.width,
                height = i.height
            ))
        return lst

    @staticmethod
    def cmd_pullgroup(q, groupName, screen=None):
        """
            Pull a group to a specified screen.

            Examples:

            Pull group "a" to the current screen:
                
                pullgroup("a")

            Pull group "a" to screen 0:
        
                pullgroup("a", 0)
        """
        if not screen:
            screen = q.currentScreen
        group = q.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s"%groupName)
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
            Simulates a keypress on the focused window. The first argument is a
            list of modifier specification strings, the second argument is a
            key specification.  Modifiers can be one of "shift", "lock",
            "control" and "mod1" through "mod5".

            Examples:

                simulate_keypress(["control", "mod2"], "k")
        """
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            raise command.CommandError("Unknown key: %s"%key)
        keycode = q.display.keysym_to_keycode(keysym)
        try:
            mask = utils.translateMasks(modifiers)
        except QTileError, v:
            return str(v)
        if q.currentClient:
            win = q.currentClient.window
        else:
            win = q.root
        e = event.KeyPress(
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
        q.display.sync()

    @staticmethod
    def cmd_spawn(q, cmd):
        """
            Run cmd in a shell.

            Example:

                spawn("firefox")
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
        """
            Sync the X display. Should only be used for development.
        """
        q.display.sync()

    @staticmethod
    def cmd_restart(q):
        #q.display.sync()
        pass

    @staticmethod
    def cmd_debug(q):
        """
            Toggle qtile debug logging. Returns "on" or "off" to indicate the
            resulting debug status.
        """
        if q.debug:
            q.debug = False
            return "off"
        else:
            q.debug = True
            return "on"

    @staticmethod
    def cmd_log(q, n=None):
        """
            Return the last n log records, where n is all by default.

            Examples:
                
                log(5)
                log()
        """
        if n and len(q.log.log) > n:
            return q.log.log[-n:]
        else:
            return q.log.log

    @staticmethod
    def cmd_report(q, msg="None", path="~/qtile_crashreport"):
        """
            Write a qtile crash report. Optional arguments are the message that
            should head the report, and the path of the file to write to.

            Examples:
                
                report()
                report(msg="My messasge")
                report(msg="My message", path="~/myreport")
        """
        q.writeReport(msg, path, True)
