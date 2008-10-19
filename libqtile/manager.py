# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime, subprocess, sys, operator, os, traceback
import select
import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X, XK
import Xlib.protocol.event as event
import command, utils, window, confreader

class QTileError(Exception): pass


class Event:
    events = set(
        [
            "setgroup",
            "focus_change",
            "window_add",
            "window_name_change",
        ]
    )
    def __init__(self, qtile):
        self.qtile = qtile
        self.subscriptions = {}

    def subscribe(self, event, func):
        if event not in self.events:
            raise QTileError("Unknown event: %s"%event)
        lst = self.subscriptions.setdefault(event, [])
        if not func in lst:
            lst.append(func)

    def fire(self, event, *args, **kwargs):
        if event not in self.events:
            raise QTileError("Unknown event: %s"%event)
        self.qtile.log.add("Internal event: %s(%s, %s)"%(event, args, kwargs))
        for i in self.subscriptions.get(event, []):
            i(*args, **kwargs)


class Key:
    def __init__(self, modifiers, key, *commands):
        """
            :modifiers A list of modifier specifications. Modifier
            specifications are one of: "shift", "lock", "control", "mod1",
            "mod2", "mod3", "mod4", "mod5".
            :key A key specification, e.g. "a", "Tab", "Return", "space".
            :*commands A list of __libqtile.command._Call__ objects. If multiple
            Call objects are specified, they are tried in sequence.
        """
        self.modifiers, self.key, self.commands = modifiers, key, commands
        self.keysym = XK.string_to_keysym(key)
        if self.keysym == 0:
            raise QTileError("Unknown key: %s"%key)
        self.modmask = utils.translateMasks(self.modifiers)
    
    def __repr__(self):
        return "Key(%s, %s)"%(self.modifiers, self.key)


class Screen(command.CommandObject):
    group = None
    def __init__(self, top=None, bottom=None, left=None, right=None):
        """
            :top An instance of bar.Gap or bar.Bar or None.
            :bottom An instance of bar.Gap or bar.Bar or None.
            :left An instance of bar.Gap or None.
            :right An instance of bar.Gap or None.
        """
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right

    def _configure(self, qtile, index, x, y, width, height, group, event):
        self.qtile, self.event = qtile, event
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self, event)

    @property
    def gaps(self):
        lst = []
        for i in [self.top, self.bottom, self.left, self.right]:
            if i:
                lst.append(i)
        return lst

    @property
    def dx(self):
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def setGroup(self, group):
        if group.screen == self:
            return
        elif group.screen:
            tmpg = self.group
            tmps = group.screen
            tmps.group = tmpg
            tmpg._setScreen(tmps)
            self.group = group
            group._setScreen(self)
        else:
            if self.group is not None:
                self.group._setScreen(None)
            self.group = group
            group._setScreen(self)
        self.event.fire("setgroup")
        self.qtile.event.fire("focus_change")

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.currentWindow
            else:
                for i in self.group.windows:
                    if i.window.id == sel:
                        return i
        elif name == "bar":
            if sel not in ["top", "bottom", "left", "right"]:
                return None
            else:
                return getattr(self, sel)

    def cmd_info(self):
        return dict(
            index=self.index
        )


class Group(command.CommandObject):
    def __init__(self, name, layouts, qtile):
        self.name, self.qtile = name, qtile
        self.screen = None
        self.layouts = [i.clone(self) for i in layouts]
        self.currentLayout = 0
        self.currentWindow = None
        self.windows = set()

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    def nextLayout(self):
        self.currentLayout = (self.currentLayout + 1)%(len(self.layouts))
        self.layoutAll()

    def layoutAll(self):
        self.disableMask(X.EnterWindowMask)
        if self.screen and len(self.windows):
            for i in self.windows:
                self.layout.configure(i)
            if self.currentWindow:
                self.currentWindow.focus(False)
        self.resetMask()

    def _setScreen(self, screen):
        self.screen = screen
        if self.screen:
            self.layoutAll()
        else:
            self.hide()

    def hide(self):
        self.screen = None
        for i in self.windows:
            i.hide()

    def disableMask(self, mask):
        for i in self.windows:
            i.disableMask(mask)

    def resetMask(self):
        for i in self.windows:
            i.resetMask()

    def focus(self, window, warp):
        if window and not window in self.windows:
            return
        if not window:
            self.currentWindow = None
        else:
            self.currentWindow = window
        self.layout.focus(window)
        self.qtile.event.fire("focus_change")
        self.layoutAll()

    def info(self):
        return dict(
            name = self.name,
            focus = self.currentWindow.name if self.currentWindow else None,
            windows = [i.name for i in self.windows],
            layout = self.layout.name,
            screen = self.screen.index if self.screen else None
        )

    def add(self, window):
        self.qtile.event.fire("window_add")
        self.windows.add(window)
        window.group = self
        for i in self.layouts:
            i.add(window)
        self.focus(window, True)

    def remove(self, window):
        self.windows.remove(window)
        window.group = None
        for i in self.layouts:
            i.remove(window)
        if self.currentWindow is window:
            self.focus(None, False)
        self.layoutAll()

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.layout
            else:
                return utils.lget(self.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.currentWindow
            else:
                for i in self.windows:
                    if i.window.id == sel:
                        return i
        elif name == "screen":
            if sel is not None:
                return None
            else:
                return self.screen

    def cmd_info(self):
        return dict(name=self.name)

    def cmd_toscreen(self, screen=None):
        """
            Pull a group to a specified screen.

            :screen Screen offset. If not specified, we assume the current screen.

            Examples:

            Pull group to the current screen:
                
                toscreen()

            Pull group to screen 0:
        
                toscreen(0)
        """
        if not screen:
            screen = self.qtile.currentScreen
        else:
            screen = self.screens[screen]
        screen.setGroup(self)


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


class QTile(command.CommandObject):
    debug = False
    _exit = False
    _testing = False
    _logLength = 100 
    def __init__(self, config, displayName=None, fname=None):
        if not displayName:
            displayName = os.environ.get("DISPLAY")
            if not displayName:
                raise QTileError("No DISPLAY set.")
        if not fname:
            if not "." in displayName:
                displayName = displayName + ".0"
            fname = os.path.join("~", command.SOCKBASE%displayName)
            fname = os.path.expanduser(fname)
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
        self.event = Event(self)

        self.atoms = dict(
            internal = self.display.intern_atom("QTILE_INTERNAL"),
            python = self.display.intern_atom("QTILE_PYTHON")
        )
        self.windowMap = {}
        self.internalMap = {}
        self.widgetMap = {}
        self.groupMap = {}

        self.groups = []
        for i in self.config.groups:
            g = Group(i, self.config.layouts, self)
            self.groups.append(g)
            self.groupMap[g.name] = g

        self.currentScreen = None
        self.screens = []
        if self.display.has_extension("XINERAMA"):
            for i, s in enumerate(self.display.xinerama_query_screens().screens):
                if i+1 > len(config.screens):
                    scr = Screen()
                else:
                    scr = config.screens[i]
                if not self.currentScreen:
                    self.currentScreen = scr
                scr._configure(
                    self,
                    i,
                    s["x"],
                    s["y"],
                    s["width"],
                    s["height"],
                    self.groups[i],
                    self.event
                )
                self.screens.append(scr)
        else:
            if config.screens:
                s = config.screens[0]
            else:
                s = Screen()
            self.currentScreen = s
            s._configure(
                self,
                0, 0, 0,
                defaultScreen.width_in_pixels,
                defaultScreen.height_in_pixels,
                self.groups[0],
                self.event
            )
            self.screens.append(s)
        self.currentScreen = self.screens[0]

        self.display.set_error_handler(self.initialErrorHandler)
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
        # Now install the real error handler
        self.display.set_error_handler(self.errorHandler)

        self.server = command._Server(self.fname, self, config)
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

    def registerWidget(self, w):
        """
            Register a bar widget. If a widget with the same name already
            exists, this raises a ConfigError.
        """
        if w.name:
            if self.widgetMap.has_key(w.name):
                raise confreader.ConfigError("Duplicate widget name: %s"%w.name)
            self.widgetMap[w.name] = w

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

    def _eventStr(self, e):
        """
            Returns a somewhat less verbose descriptive event string.
        """
        s = str(e)
        s = s.replace("Xlib.protocol.event.", "")
        s = s.replace("Xlib.display.", "")
        return s

    def loop(self):
        try:
            while 1:
                fds, _, _ = select.select(
                                [self.server.sock, self.display.fileno()],
                                [], [], 0.1
                            )
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
                    ename = e.__class__.__name__

                    c = None
                    if hasattr(e, "window"):
                        c = self.windowMap.get(e.window) or self.internalMap.get(e.window)
                    if c and hasattr(c, "handle_%s"%ename):
                        h = getattr(c, "handle_%s"%ename)
                    else:
                        h = getattr(self, "handle_%s"%ename, None)
                    if h:
                        self.log.add("Handling: %s"%self._eventStr(e))
                        h(e)
                    elif e.type in self.ignoreEvents:
                        pass
                    else:
                        self.log.add("Unknown event: %s"%self._eventStr(e))
        except:
            # We've already written a report.
            if not self._exit:
                self.writeReport(traceback.format_exc())

    def handle_KeyPress(self, e):
        keysym =  self.display.keycode_to_keysym(e.detail, 0)
        k = self.keyMap.get((keysym, e.state))
        if not k:
            print >> sys.stderr, "Ignoring unknown keysym: %s"%keysym
            return
        for i in k.commands:
            if i.check(self):
                status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    s = "KB command error %s: %s"%(i.name, val)
                    self.log.add(s)
                    print >> sys.stderr, s
        else:
            return

    def handle_ConfigureRequest(self, e):
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

    def handle_MappingNotify(self, e):
        self.display.refresh_keyboard_mapping(e)
        if e.request == X.MappingKeyboard:
            self.grabKeys()

    def handle_MapRequest(self, e):
        self.manage(e.window)

    def handle_DestroyNotify(self, e):
        self.unmanage(e.window)

    def handle_UnmapNotify(self, e):
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
        suffix = 0
        base = p = os.path.expanduser(path)
        while 1:
            if not os.path.exists(p):
                break
            p = base + ".%s"%suffix
            suffix += 1
        f = open(p, "a+")
        print >> f, "*** QTILE REPORT", datetime.datetime.now()
        print >> f, "Message:", m
        print >> f, "Last %s events:"%self.log.length
        self.log.write(f, "\t")
        f.close()

    def initialErrorHandler(self, e, v):
        self._exit = True

    _ignoreErrors = set([
        Xlib.error.BadWindow,
        Xlib.error.BadAccess
    ])
    def errorHandler(self, e, v):
        if e.__class__ in self._ignoreErrors:
            return
        if self._testing:
            print >> sys.stderr, "Server Error:", (e, v)
        else:
            self.writeReport((e, v))
        self._exit = True

    def _items(self, name):
        if name == "group":
            return self.groupMap.keys()
        elif name == "layout":
            return range(len(self.currentGroup.layouts))
        elif name == "widget":
            return self.widgetMap.keys()
        elif name == "bar":
            lst = []
            for i in ["top", "bottom", "left", "right"]:
                if getattr(self.currentScreen, i):
                    lst.append(i)
            return lst
        elif name == "window":
            return self.listWID()
        elif name == "screen":
            return range(len(self.screens))

    def _select(self, name, sel):
        if name == "group":
            if sel is not None:
                obj = self.groupMap.get(sel)
            else:
                obj = self.currentGroup
        elif name == "layout":
            if sel is not None:
                obj = utils.lget(self.currentGroup.layouts, sel)
            else:
                obj = self.currentGroup.layout
        elif name == "widget":
            obj = self.widgetMap.get(sel)
        elif name == "bar":
            if sel not in ["top", "bottom", "left", "right"]:
                obj = None
            else:
                obj = getattr(self.currentScreen, sel)
        elif name == "window":
            if sel is not None:
                obj = self.clientFromWID(sel)
            else:
                obj = self.currentWindow
        elif name == "screen":
            if sel is not None:
                obj = utils.lget(self.screens, sel)
            else:
                obj = self.currentScreen
        else:
            obj = None
        return obj

    def listWID(self):
        return [i.window.id for i in self.windowMap.values() + self.internalMap.values()]

    def clientFromWID(self, wid):
        all = self.windowMap.values() + self.internalMap.values()
        for i in all:
            if i.window.id == wid:
                return i
        return None

    def cmd_debug(self):
        """
            Toggle qtile debug logging. Returns "on" or "off" to indicate the
            resulting debug status.
        """
        if self.debug:
            self.debug = False
            self.log.debug = None
            return "off"
        else:
            self.debug = True
            self.log.debug = sys.stderr
            return "on"

    def cmd_groups(self):
        """
            Return a dictionary containing information for all groups.

            Example:
                
                groups()
        """
        d = {}
        for i in self.groups:
            d[i.name] = i.info()
        return d

    def cmd_internal(self):
        """
            Return info for each internal window (bars, for example).
        """
        return [i.info() for i in self.internalMap.values()]

    def cmd_list_widgets(self):
        """
            List of all addressible widget names.
        """
        return self.widgetMap.keys()

    def cmd_log(self, n=None):
        """
            Return the last n log records, where n is all by default.

            Examples:
                
                log(5)

                log()
        """
        if n and len(self.log.log) > n:
            return self.log.log[-n:]
        else:
            return self.log.log

    def cmd_log_clear(self):
        """
            Clears the internal log.
        """
        self.log.clear()

    def cmd_log_getlength(self):
        """
            Returns the configured size of the internal log.
        """
        return self.log.length

    def cmd_log_setlength(self, n):
        """
            Sets the configured size of the internal log.
        """
        return self.log.setLength(n)

    def cmd_nextlayout(self, group=None):
        """
            Switch to the next layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groupMap.get(group)
        else:
            group = self.currentGroup
        group.nextLayout()

    def cmd_report(self, msg="None", path="~/qtile_crashreport"):
        """
            Write a qtile crash report. 
            
            :msg Message that should head the report
            :path Path of the file to write to

            Examples:
                
                report()

                report(msg="My messasge")

                report(msg="My message", path="~/myreport")
        """
        self.writeReport(msg, path, True)

    def cmd_screens(self):
        """
            Return a list of dictionaries providing information on all screens.
        """
        lst = []
        for i in self.screens:
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

    def cmd_simulate_keypress(self, modifiers, key):
        """
            Simulates a keypress on the focused window. 
            
            :modifiers A list of modifier specification strings. Modifiers can
            be one of "shift", "lock", "control" and "mod1" - "mod5".
            :key Key specification.  

            Examples:

                simulate_keypress(["control", "mod2"], "k")
        """
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            raise command.CommandError("Unknown key: %s"%key)
        keycode = self.display.keysym_to_keycode(keysym)
        try:
            mask = utils.translateMasks(modifiers)
        except QTileError, v:
            return str(v)
        if self.currentWindow:
            win = self.currentWindow.window
        else:
            win = self.root
        e = event.KeyPress(
                state = mask,
                detail = keycode,

                root = self.root,
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
        self.display.sync()

    def cmd_spawn(self, cmd):
        """
            Run cmd in a shell.

            Example:

                spawn("firefox")
        """
        try:
            subprocess.Popen([cmd], shell=True)
        except Exception, v:
            print type(v), v

    def cmd_status(self):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    def cmd_sync(self):
        """
            Sync the X display. Should only be used for development.
        """
        self.display.sync()

    def cmd_to_screen(self, n):
        """
            Warp to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return self.toScreen(n)

    def cmd_windows(self):
        """
            Return info for each client window.
        """
        return [i.info() for i in self.windowMap.values()]
