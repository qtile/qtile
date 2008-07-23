import datetime, subprocess, sys, operator, os, traceback
import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X, XK, Xatom
import Xlib.protocol.event as event
import command, utils, window

class QTileError(Exception): pass


class Key:
    def __init__(self, modifiers, key, *commands):
        """
            If multiple Call objects are specified, they are tried in sequence.
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
    def __init__(self, top=None, bottom=None, left=None, right=None):
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right

    def _configure(self, qtile, index, x, y, width, height, group):
        self.qtile = qtile
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)
        for i in [self.top, self.bottom, self.left, self.right]:
            if i:
                i._configure(qtile, self)

    @property
    def dx(self):
        return self.x + self.left.width if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.width if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.width
        if self.right:
            val -= self.right.width
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.width
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
        self.currentWindow = None

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
            if self.currentWindow:
                self.currentWindow.focus(False)
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
        idx = (self.index(self.currentWindow) + 1) % len(self)
        self.focus(self[idx], False)

    def disableMask(self, mask):
        for i in self:
            i.disableMask(mask)

    def resetMask(self):
        for i in self:
            i.resetMask()

    def focus(self, window, warp):
        if window and not window in self:
            return
        if not window:
            self.currentWindow = None
        else:
            self.currentWindow = window
        self.layout.focus(window)
        self.layoutAll()

    def info(self):
        return dict(
            name = self.name,
            focus = self.currentWindow.name if self.currentWindow else None,
            windows = [i.name for i in self],
            layout = self.layout.name,
            screen = self.screen.index if self.screen else None
        )

    # List-like operations
    def add(self, window):
        if self.currentWindow:
            offset = self.index(self.currentWindow)
        else:
            offset = 0
        self.insert(offset, window)
        window.group = self
        for i in self.layouts:
            i.add(window)
        self.focus(window, True)

    def remove(self, window):
        if self.currentWindow is window:
            if len(self) > 1:
                self.focusNext()
            else:
                self.focus(None, False)
        list.remove(self, window)
        window.group = None
        for i in self.layouts:
            i.remove(window)
        self.layoutAll()


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

    def setLength(self, l):
        self.length = l
        if len(self.log) > l:
            self.log = self.log[-l:]

    def clear(self):
        self.log = []


class QTile:
    debug = False
    _exit = False
    _testing = False
    _logLength = 100 

    def __init__(self, config, displayName, fname):
        self.display = Xlib.display.Display(displayName)
        self.config, self.fname = config, fname
        self.log = Log(
            self._logLength,
            sys.stderr if self.debug else None
        )
        defaultScreen = self.display.screen(
                    self.display.get_default_screen()
               )
        self.root = defaultScreen.root

        self.atoms = dict(
            internal = self.display.intern_atom("QTILE_INTERNAL"),
            python = self.display.intern_atom("QTILE_PYTHON")
        )
        self.windowMap = {}
        self.internalMap = {}

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
                    self,
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
                self,
                0, 0, 0,
                defaultScreen.width_in_pixels,
                defaultScreen.height_in_pixels,
                self.groups[0]
            )
            self.screens.append(s)
        self.currentScreen = self.screens[0]

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
            # DWM handles this to help "broken focusing windows".
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
    def currentWindow(self):
        return self.currentScreen.group.currentWindow

    def scan(self):
        r = self.root.query_tree()
        for i in r.children:
            a = i.get_attributes()
            if a.map_state == Xlib.X.IsViewable:
                self.manage(i)

    def unmanage(self, window):
        c = self.windowMap.get(window)
        if c:
            c.group.remove(c)
            del self.windowMap[window]

    def manage(self, w):
        attrs = w.get_attributes()
        if attrs and attrs.override_redirect:
            return
        if w.get_full_property(self.atoms["internal"], self.atoms["python"]):
            if not w in self.internalMap:
                c = window.Internal(w, self)
                self.internalMap[w] = c
        else:
            if not w in self.windowMap:
                c = window.Window(w, self)
                self.windowMap[w] = c
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
            self.log.add(s)
            print >> sys.stderr, s

    def configureRequest(self, e):
        c = self.windowMap.get(e.window)
        if c and c.group.screen:
            c.group.focus(c, False)
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
        c = self.windowMap.get(e.window)
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
        c = self.windowMap.get(e.window)
        if c:
            self.currentScreen.group.focus(c, False)
            if self.currentScreen != c.group.screen:
                self.toScreen(c.group.screen.index)

    def mapRequest(self, e):
        self.manage(e.window)

    def destroyNotify(self, e):
        self.unmanage(e.window)

    def unmapNotify(self, e):
        if e.event == self.root and e.send_event:
            self.unmanage(e.window)

    def toScreen(self, n):
        if len(self.screens) < n-1:
            return
        self.currentScreen = self.screens[n]
        self.currentGroup.focus(
            self.currentWindow,
            True
        )

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
    def cmd_windows(q):
        """
            Return info for each client window.
        """
        return [i.info() for i in q.windowMap.values()]

    @staticmethod
    def cmd_internal(q):
        """
            Return info for each internal window.
        """
        return [i.info() for i in q.internalMap.values()]

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
    def cmd_groups(q):
        """
            Return a dictionary containing information for all groups.

            Example:
                
                groups()
        """
        d = {}
        for i in q.groups:
            d[i.name] = i.info()
        return d

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
                height = i.height,
                gaps = dict(
                    top = i.top.geometry() if i.top else None,
                    bottom = i.bottom.geometry() if i.bottom else None,
                    left = i.left.geometry() if i.left else None,
                    right = i.right.geometry() if i.right else None,
                )
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
        if q.currentWindow:
            win = q.currentWindow.window
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
        window = q.currentScreen.group.currentWindow
        if window:
            window.kill()

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
    def cmd_log_clear(q):
        """
            Clears the internal log.

            Examples:
                
                log_clear()
        """
        q.log.clear()

    @staticmethod
    def cmd_log_setlength(q, n):
        """
            Sets the configured size of the internal log.

            Examples:
                
                log_setlength(10)
        """
        return q.log.setLength(n)

    @staticmethod
    def cmd_log_getlength(q):
        """
            Clears the configured size of the internal log.

            Examples:
                
                log_getlength()
        """
        return q.log.length

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

    @staticmethod
    def cmd_inspect(q, windowID=None):
        """
            Tells you more than you ever wanted to know about a window window.
            If windowID is specified, it should be the integer X window
            identifier. The current focus is inspected by default.

                inspect()
                inspect(0x600005)
        """
        if windowID:
            all = q.windowMap.values() + q.internalMap.values()
            for i in all:
                if i.window.id == windowID:
                    c = i
                    break
            else:
                raise command.CommandError("No such window: %s"%windowID)
        else:
            c = q.currentWindow
            if not c:
                raise command.CommandError("No current focus.")

        a = c.window.get_attributes()
        attrs = {
            "backing_store": a.backing_store,
            "visual": a.visual,
            "class": a.win_class,
            "bit_gravity": a.bit_gravity,
            "win_gravity": a.win_gravity,
            "backing_bit_planes": a.backing_bit_planes,
            "backing_pixel": a.backing_pixel,
            "save_under": a.save_under,
            "map_is_installed": a.map_is_installed,
            "map_state": a.map_state,
            "override_redirect": a.override_redirect,
            #"colormap": a.colormap,
            "all_event_masks": a.all_event_masks,
            "your_event_mask": a.your_event_mask,
            "do_not_propagate_mask": a.do_not_propagate_mask
        }
        props = [q.display.get_atom_name(x) for x in c.window.list_properties()]
        
        h = c.window.get_wm_normal_hints()
        if h:
            normalhints = dict(
                flags = h.flags,
                min_width = h.min_width,
                min_height = h.min_height,
                max_width = h.max_width,
                max_height = h.max_height,
                width_inc = h.width_inc,
                height_inc = h.height_inc,
                min_aspect = dict(num=h.min_aspect["num"], denum=h.min_aspect["denum"]),
                max_aspect = dict(num=h.max_aspect["num"], denum=h.max_aspect["denum"]),
                base_width = h.base_width,
                base_height = h.base_height,
                win_gravity = h.win_gravity
            )
        else:
            normalhints = None
        
        h = c.window.get_wm_hints()
        if h:
            hints = dict(
                flags = h.flags,
                input = h.input,
                initial_state = h.initial_state,
                icon_window = h.icon_window.id,
                icon_x = h.icon_x,
                icon_y = h.icon_y,
                window_group = h.window_group.id
            )
        else:
            hints = None

        state = c.window.get_wm_state()

        return dict(
            attributes=attrs,
            properties=props,
            name = c.window.get_wm_name(),
            wm_class = c.window.get_wm_class(),
            wm_transient_for = c.window.get_wm_transient_for(),
            protocols = [q.display.get_atom_name(x) for x in c.window.get_wm_protocols()],
            wm_icon_name = c.window.get_wm_icon_name(),
            wm_client_machine = c.window.get_wm_client_machine(),
            normalhints = normalhints,
            hints = hints,
            state = state
        )

    @staticmethod
    def cmd_layoutinfo(q, group=None, layout=None):
        """

            Return layout info. The optional group argument is a group name.
            The optional layout argument is an integer layout offset.If
            neither are specified the current group and layout is used.

            Examples:
                
                layoutinfo()
                layoutinfo("a", 1)
        """
        if group:
            group = q.groupMap.get(group)
            if group is None:
                raise command.CommandError("No such group: %s"%groupName)
        else:
            group = q.currentGroup
        if layout:
            if layout > (len(group.layouts) - 1):
                raise command.CommandError("Invalid layout offset: %s."%layout)
            layout = group.layouts[layout]
        else:
            layout = group.layout
        return layout.info()
                
