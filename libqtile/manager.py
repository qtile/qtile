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
import command, utils, window, config

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
            :*commands A list of __libqtile.command.Call__ objects. If multiple
            Call objects are specified, they are tried in sequence.
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


class Group:
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
                raise config.ConfigError("Duplicate widget name: %s"%w.name)
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
                status, val = self.server.call((i.command, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    s = "KB command error %s: %s"%(i.command, val)
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


class _BaseCommands(command.Commands):
    @staticmethod
    def cmd_barinfo(q, screen=None):
        """
            Returns a dictionary of information regarding the bar on the
            specified screen.

            :screen Screen integer offset. If none is specified, the current
            screen is assumed.
        """
        if not screen:
            screen = q.currentScreen
        else:
            screen = self.screens[screen]
        return dict(
            top = screen.top.info() if screen.top else None,
            bottom = screen.bottom.info() if screen.bottom else None,
            left = screen.left.info() if screen.left else None,
            right = screen.right.info() if screen.right else None,
        )

    @staticmethod
    def cmd_current_screen(q):
        """
            Return current screen number.
        """
        return q.screens.index(q.currentScreen)

    @staticmethod
    def cmd_debug(q):
        """
            Toggle qtile debug logging. Returns "on" or "off" to indicate the
            resulting debug status.
        """
        if q.debug:
            q.debug = False
            q.log.debug = None
            return "off"
        else:
            q.debug = True
            q.log.debug = sys.stderr
            return "on"

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
    def cmd_inspect(q, windowID=None):
        """
            Tells you more than you ever wanted to know about a window window.
            If windowID is specified, it should be the integer X window
            identifier. The current focus is inspected by default.

            Example:

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
    def cmd_internal(q):
        """
            Return info for each internal window (bars, for example).
        """
        return [i.info() for i in q.internalMap.values()]

    @staticmethod
    def cmd_kill(q):
        """
            Kill the window that currently has focus.
        """
        window = q.currentScreen.group.currentWindow
        if window:
            window.kill()

    @staticmethod
    def cmd_layoutinfo(q, group=None, layout=None):
        """
            Return layout info. 
            
            :group Group name.
            :layout Integer layout offset.

            If neither are specified the current group and layout is used.

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

    @staticmethod
    def cmd_list_widgets(q):
        """
            List of all addressible widget names.
        """
        return q.widgetMap.keys()

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
        """
        q.log.clear()

    @staticmethod
    def cmd_log_getlength(q):
        """
            Returns the configured size of the internal log.
        """
        return q.log.length

    @staticmethod
    def cmd_log_setlength(q, n):
        """
            Sets the configured size of the internal log.
        """
        return q.log.setLength(n)

    @staticmethod
    def cmd_nextlayout(q, group=None):
        """
            Switch to the next layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = q.groupMap.get(group)
        else:
            group = q.currentGroup
        group.nextLayout()

    @staticmethod
    def cmd_pullgroup(q, group, screen=None):
        """
            Pull a group to a specified screen.

            :group Group name.
            :screen Screen offset. If not specified, we assume the current screen.

            Examples:

            Pull group "a" to the current screen:
                
                pullgroup("a")

            Pull group "a" to screen 0:
        
                pullgroup("a", 0)
        """
        if not screen:
            screen = q.currentScreen
        else:
            screen = self.screens[screen]
        group = q.groupMap.get(group)
        if group is None:
            raise command.CommandError("No such group: %s"%group)
        screen.setGroup(group)

    @staticmethod
    def cmd_report(q, msg="None", path="~/qtile_crashreport"):
        """
            Write a qtile crash report. 
            
            :msg Message that should head the report
            :path Path of the file to write to

            Examples:
                
                report()

                report(msg="My messasge")

                report(msg="My message", path="~/myreport")
        """
        q.writeReport(msg, path, True)

    @staticmethod
    def cmd_screens(q):
        """
            Return a list of dictionaries providing information on all screens.
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
    def cmd_simulate_keypress(q, modifiers, key):
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
    def cmd_status(q):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    @staticmethod
    def cmd_sync(q):
        """
            Sync the X display. Should only be used for development.
        """
        q.display.sync()

    @staticmethod
    def cmd_to_screen(q, n):
        """
            Warp to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return q.toScreen(n)

    @staticmethod
    def cmd_window_to_group(q, groupName):
        """
            Move focused window to a specified group.

            Examples:

                window_to_group("a")
        """
        group = q.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s"%groupName)
        if q.currentWindow and q.currentWindow.group is not group:
            w = q.currentWindow
            q.currentWindow.group.remove(w)
            group.add(w)

    @staticmethod
    def cmd_windows(q):
        """
            Return info for each client window.
        """
        return [i.info() for i in q.windowMap.values()]
