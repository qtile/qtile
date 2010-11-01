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
import datetime, subprocess, sys, os, traceback
import select, contextlib
import xcbq
import xcb.xproto, xcb.xinerama
import xcb
from xcb.xproto import EventMask
import command, utils, window, confreader, hook


class QtileError(Exception): pass


class Defaults:
    def __init__(self, *defaults):
        """
            defaults: A list of (name, value, description) tuples.
        """
        self.defaults = defaults

    def load(self, target, config):
        """
            Loads a dict of attributes, using specified defaults, onto target.
        """
        for i in self.defaults:
            val = config.get(i[0], i[1])
            setattr(target, i[0], val)


class Key:
    """
        Defines a keybinding.
    """
    def __init__(self, modifiers, key, *commands):
        """
            - modifiers: A list of modifier specifications. Modifier
            specifications are one of: "shift", "lock", "control", "mod1",
            "mod2", "mod3", "mod4", "mod5".

            - key: A key specification, e.g. "a", "Tab", "Return", "space".

            - *commands: A list of lazy command objects generated with the
            command.lazy helper. If multiple Call objects are specified, they
            are run in sequence.
        """
        self.modifiers, self.key, self.commands = modifiers, key, commands
        if key not in xcbq.keysyms:
            raise QtileError("Unknown key: %s"%key)
        self.keysym = xcbq.keysyms[key]
        try:
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise QtileError(v)
    
    def __repr__(self):
        return "Key(%s, %s)"%(self.modifiers, self.key)


class Screen(command.CommandObject):
    """
        A physical screen, and its associated paraphernalia.
    """
    group = None
    def __init__(self, top=None, bottom=None, left=None, right=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.
            
            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).
        """
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right

    def _configure(self, qtile, index, x, y, width, height, group):
        self.qtile = qtile
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self)

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
        hook.fire("setgroup")
        hook.fire("focus_change")

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.group.windows]
        elif name == "bar":
            return False, [x.position for x in self.gaps]

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
                    if i.window.wid == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.group.layoutAll()

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x = self.x,
            y = self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """
            Resize the screen.
        """
        self.resize(x, y, w, h)


class Group(command.CommandObject):
    """
        A group is a container for a bunch of windows, analogous to workspaces
        in other window managers. Each client window managed by the window
        manager belongs to exactly one group.
    """
    def __init__(self, name, layout=None):
        self.name = name
        self.customLayout = layout  # will be set on _configure

    def _configure(self, layouts, qtile):
        self.screen = None
        self.currentLayout = 0
        self.currentWindow = None
        self.windows = set()
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        if self.customLayout is not None:
            self.layout = self.customLayout
            self.customLayout = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    @layout.setter
    def layout(self, layout):
        """
            "layout" is a string with matching the name of a Layout object.
        """
        for index, obj in enumerate(self.layouts):
            if obj.name == layout:
                self.currentLayout = index
                self.layoutAll()
                return
        raise ValueError("No such layout: %s"%layout)

    def nextLayout(self):
        self.currentLayout = (self.currentLayout + 1)%(len(self.layouts))
        self.layoutAll()

    def layoutAll(self):
        with self.disableMask(xcb.xproto.EventMask.EnterWindow):
            if self.screen and len(self.windows):
                self.layout.layout(self.windows)
                if self.currentWindow:
                    self.currentWindow.focus(False)

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

    @contextlib.contextmanager
    def disableMask(self, mask):
        for i in self.windows:
            i._disableMask(mask)
        yield
        for i in self.windows:
            i._resetMask()

    def focus(self, window, warp):
        if window and not window in self.windows:
            return
        if not window:
            self.currentWindow = None
        else:
            self.currentWindow = window
        self.layout.focus(window)
        hook.fire("focus_change")
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
        hook.fire("group_window_add")
        self.windows.add(window)
        window.group = self
        for i in self.layouts:
            i.add(window)
        self.focus(window, True)

    def remove(self, window):
        self.windows.remove(window)
        window.group = None
        nextfocus = None
        for i in self.layouts:
            if i is self.layout:
                nextfocus = i.remove(window)
            else:
                i.remove(window)
        self.focus(nextfocus, True)
        self.layoutAll()

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.windows]
        elif name == "screen":
            return True, None

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
                    if i.window.wid == sel:
                        return i
        elif name == "screen":
            return self.screen

    def cmd_setlayout(self, layout):
        self.layout = layout

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return dict(
                name=self.name,
                screen = self.screen.index if self.screen else None,
                windows = [i.window.wid for i in self.windows]
               )

    def cmd_toscreen(self, screen=None):
        """
            Pull a group to a specified screen.

            - screen: Screen offset. If not specified, we assume the current screen.

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

    def _dirGroup(self, direction):
        currentgroup = self.qtile.groups.index(self)
        nextgroup = (currentgroup + direction) % len(self.qtile.groups)
        return self.qtile.groups[nextgroup]

    def prevGroup(self):
        return self._dirGroup(-1)
    
    def nextGroup(self):
        return self._dirGroup(1)
    
    # FIXME cmd_nextgroup and cmd_prevgroup should be on the Screen object.
    def cmd_nextgroup(self):
        """
            Switch to the next group.
        """
        n = self.nextGroup()
        self.qtile.currentScreen.setGroup(n)
        return n.name

    def cmd_prevgroup(self):
        """
            Switch to the previous group.
        """
        n = self.prevGroup()
        self.qtile.currentScreen.setGroup(n)
        return n.name

    def cmd_unminimise_all(self):
        """
            Unminimise all windows in this group.
        """
        for w in self.windows:
            w.minimised = False
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


class Qtile(command.CommandObject):
    """
        This object is the __root__ of the command graph.
    """
    debug = False
    _exit = False
    _testing = False
    _logLength = 100 
    def __init__(self, config, displayName=None, fname=None, testing=False):
        self._testing = testing
        if not displayName:
            displayName = os.environ.get("DISPLAY")
            if not displayName:
                raise QtileError("No DISPLAY set.")

        if not fname:
            # Dots might appear in the host part of the display name
            # during remote X sessions. Let's strip the host part first.
            displayNum = displayName.partition(":")[2]
            if not "." in displayNum:
                displayName = displayName + ".0"
            fname = command.find_sockfile(displayName)

        self.conn = xcbq.Connection(displayName)
        self.config, self.fname = config, fname
        self.log = Log(
                self._logLength,
                sys.stderr if self.debug else None
            )
        hook.init(self)

        self.windowMap = {}
        self.widgetMap = {}
        self.groupMap = {}
        self.groups = []

        # Because we only do Xinerama multi-screening, we can assume that the first
        # screen's root is _the_ root.
        self.root = self.conn.default_screen.root
        self.root.set_attribute(
            eventmask = EventMask.StructureNotify |\
                        EventMask.SubstructureNotify |\
                        EventMask.SubstructureRedirect |\
                        EventMask.EnterWindow |\
                        EventMask.LeaveWindow
        )

        if config.main:
            config.main(self)

        self.groups += self.config.groups[:]
        for i in self.groups:
            i._configure(config.layouts, self)
            self.groupMap[i.name] = i

        self.currentScreen = None
        self.screens = []
        for i, s in enumerate(self.conn.pseudoscreens):
            if i+1 > len(config.screens):
                scr = Screen()
            else:
                scr = config.screens[i]
            if not self.currentScreen:
                self.currentScreen = scr
            scr._configure(
                self,
                i,
                s.x,
                s.y,
                s.width,
                s.height,
                self.groups[i],
            )
            self.screens.append(scr)

        if not self.screens:
            if config.screens:
                s = config.screens[0]
            else:
                s = Screen()
            self.currentScreen = s
            s._configure(
                self, 
                0, 0, 0,
                self.conn.default_screen.width_in_pixels,
                self.conn.default_screen.height_in_pixels,
                self.groups[0],
            )
            self.screens.append(s)
        self.currentScreen = self.screens[0]

        self.ignoreEvents = set([
            xcb.xproto.KeyReleaseEvent,
            xcb.xproto.ReparentNotifyEvent,
            xcb.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcb.xproto.MapNotifyEvent,
            xcb.xproto.LeaveNotifyEvent,
            xcb.xproto.FocusOutEvent,
            xcb.xproto.FocusInEvent,
        ])

        self.conn.flush()
        self.conn.xsync()
        self.xpoll()
        if self._exit:
            print >> sys.stderr, "Access denied: Another window manager running?"
            sys.exit(1)

        self.server = command._Server(self.fname, self, config)
        # Find the modifier mask for the numlock key, if there is one:
        nc = self.conn.keysym_to_keycode(xcbq.keysyms["Num_Lock"])
        self.numlockMask = xcbq.ModMasks[self.conn.get_modifier(nc)]
        self.validMask = ~(self.numlockMask | xcbq.ModMasks["lock"])

        self.keyMap = {}
        for i in self.config.keys:
            self.keyMap[(i.keysym, i.modmask&self.validMask)] = i

        self.grabKeys()
        self.scan()

    def addGroup(self, name):
        if name not in self.groupMap.keys():
            g = Group(name)
            self.groups.append(g)
            g._configure(self.config.layouts, self)
            self.groupMap[name] = g
            hook.fire("addgroup")
            return True
        return False

    def delGroup(self, name):
        if len(self.groups) == 1:
            raise ValueError("Can't delete all groups.")
        if name in self.groupMap.keys():
            group = self.groupMap[name]
            prev = group.prevGroup()
            for i in list(group.windows):
                i.togroup(prev.name)
            if self.currentGroup.name == name:
                self.currentGroup.cmd_prevgroup()
            self.groups.remove(group)
            del(self.groupMap[name])
            hook.fire("delgroup")

    def registerWidget(self, w):
        """
            Register a bar widget. If a widget with the same name already
            exists, this raises a ConfigError.
        """
        if w.name:
            if self.widgetMap.has_key(w.name):
                raise confreader.ConfigError("Duplicate widget name: %s"%w.name)
            self.widgetMap[w.name] = w

    @utils.LRUCache(200)
    def colorPixel(self, name):
        return self.conn.screens[0].default_colormap.alloc_color(name).pixel

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
        _, _, children = self.root.query_tree()
        for i in children:
            try:
                a = i.get_attributes()
                h = i.get_wm_hints()
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                continue
            # Are more exceptions needed now we call get_wm_hints?
            if a and a.map_state is xcb.xproto.MapState.Viewable:
                self.manage(i)
            # is this needed? can we just use wm hints?
            elif h and h.get('initial_state') in (window.NormalState, window.IconicState):
            # maybe we can prevent a wasted hints call? either:
            # a) pass hints on to 'manage' so window.py doesn't have to get them
            # b) create a function to get *just* 'initial_state'
                self.manage(i)

    def unmanage(self, window):
        c = self.windowMap.get(window)
        if c:
            hook.fire("client_killed", c)
            if hasattr(c, "group"):
                c.group.remove(c)
            del self.windowMap[window]

    def manage(self, w):
        attrs = w.get_attributes()
        internal = w.get_property("QTILE_INTERNAL")
        if attrs and attrs.override_redirect:
            return

        if not w.wid in self.windowMap:
            if internal:
                c = window.Internal(w, self)
                self.windowMap[w.wid] = c
            else:
                c = window.Window(w, self)
                hook.fire("client_new", c)
                # Window may be defunct because it's been declared static in hook.
                if c.defunct:
                    return
                self.windowMap[w.wid] = c
                # Window may have been bound to a group in the hook.
                if not c.group:
                    self.currentScreen.group.add(c)
                hook.fire("client_managed", c)
            return c

    def grabKeys(self):
        self.root.ungrab_key(None, None)
        for i in self.keyMap.values():
            code = self.conn.keysym_to_keycode(i.keysym)
            self.root.grab_key(
                code,
                i.modmask,
                True,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
            )
            if self.numlockMask:
                self.root.grab_key(
                    code,
                    i.modmask | self.numlockMask,
                    True,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                )
                self.root.grab_key(
                    code,
                    i.modmask | self.numlockMask | xcbq.ModMasks["lock"],
                    True,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                )

    def get_target_chain(self, ename, e):
        """
            Returns a chain of targets that can handle this event. The event
            will be passed to each target in turn for handling, until one of
            the handlers returns False or the end of the chain is reached.
        """
        chain = []
        handler = "handle_%s"%ename
        # Certain events expose the affected window id as an "event" attribute.
        eventEvents = [
            "EnterNotify",
            "ButtonPress",
            "KeyPress",
        ]
        c = None
        if hasattr(e, "window"):
            c = self.windowMap.get(e.window)
        if ename in eventEvents:
            c = self.windowMap.get(e.event)
        if c and hasattr(c, handler):
            chain.append(getattr(c, handler))
        if hasattr(self, handler):
            chain.append(getattr(self, handler))
        if not chain:
            self.log.add("Unknown event: %s"%ename)
        return chain

    def xpoll(self):
        while True:
            try:
                e = self.conn.conn.poll_for_event()
                if not e:
                    break
                if e.response_type == 161:
                    e = xcb.xproto.ClientMessageEvent(e)

                ename = e.__class__.__name__

                if ename.endswith("Event"):
                    ename = ename[:-5]
                if self.debug:
                    print >> sys.stderr, ename
                if not e.__class__ in self.ignoreEvents:
                    for h in self.get_target_chain(ename, e):
                        self.log.add("Handling: %s"%ename)
                        r = h(e)
                        if not r:
                            break
            except Exception, v:
                self.errorHandler(v)
                if self._exit:
                    return
                continue

    def loop(self):
        try:
            while 1:
                fds, _, _ = select.select(
                                [self.server.sock, self.conn.conn.get_file_descriptor()],
                                [], [], 0.01
                            )
                if self._exit:
                    sys.exit(1)
                self.server.receive()
                self.xpoll()
                self.conn.flush()
                hook.fire("tick")
        except:
            # We've already written a report.
            if not self._exit:
                self.writeReport(traceback.format_exc())

    def find_screen(self, x, y):
        """
            Find a screen based on the x and y offset.
        """
        for i in self.screens:
            if x >= i.x and x <= i.x + i.width and y >= i.y and y <= i.y + i.height:
                return i

    def handle_EnterNotify(self, e):
        if e.event in self.windowMap:
            return True
        s = self.find_screen(e.root_x, e.root_y)
        if s:
            self.toScreen(s.index)

    def handle_KeyPress(self, e):
        keysym = self.conn.code_to_syms[e.detail][0]
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask
        k = self.keyMap.get((keysym, state&self.validMask))
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

    def handle_ConfigureNotify(self, e):
        """
            Handle xrandr events.
        """
        screen = self.currentScreen
        if e.window == self.root.wid and e.width != screen.width and e.height != screen.height:
            screen.resize(0, 0, e.width, e.height)
            
    def handle_ConfigureRequest(self, e):
        # It's not managed, or not mapped, so we just obey it.
        cw = xcb.xproto.ConfigWindow
        args = {}
        if e.value_mask & cw.X:
            args["x"] = max(e.x, 0)
        if e.value_mask & cw.Y:
            args["y"] = max(e.y, 0)
        if e.value_mask & cw.Height:
            args["height"] = max(e.height, 0)
        if e.value_mask & cw.Width:
            args["width"] = max(e.width, 0)
        if e.value_mask & cw.BorderWidth:
            args["borderwidth"] = max(e.border_width, 0)
        w = xcbq.Window(self.conn, e.window)
        w.configure(**args)

    def handle_MappingNotify(self, e):
        self.conn.refresh_keymap()
        if e.request == xcb.xproto.Mapping.Keyboard:
            self.grabKeys()

    def handle_MapRequest(self, e):
        w = xcbq.Window(self.conn, e.window)
        c = self.manage(w)
        if c and not c.group.screen:
            return
        w.map()

    def handle_DestroyNotify(self, e):
        self.unmanage(e.window)

    def handle_UnmapNotify(self, e):
        RESPONSE_TYPE_MASK = 0x7f
        SEND_EVENT_MASK = 0x80
        if e.event != self.root.wid:
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

    _ignoreErrors = set([
        xcb.xproto.BadWindow,
        xcb.xproto.BadAccess
    ])
    def errorHandler(self, e):
        if e.__class__ in self._ignoreErrors:
            print >> sys.stderr, e
            return
        if hasattr(e.args[0], "bad_value"):
            m = "\n".join([
                "Server Error: %s"%e.__class__.__name__,
                "\tbad_value: %s"%e.args[0].bad_value,
                "\tmajor_opcode: %s"%e.args[0].major_opcode,
                "\tminor_opcode: %s"%e.args[0].minor_opcode
            ])
        else:
            m = traceback.format_exc()

        if self._testing:
            print >> sys.stderr, m
        else:
            self.writeReport(m)
        self._exit = True

    def _items(self, name):
        if name == "group":
            return True, self.groupMap.keys()
        elif name == "layout":
            return True, range(len(self.currentGroup.layouts))
        elif name == "widget":
            return False, self.widgetMap.keys()
        elif name == "bar":
            return False, [x.position for x in self.currentScreen.gaps]
        elif name == "window":
            return True, self.listWID()
        elif name == "screen":
            return True, range(len(self.screens))

    def _select(self, name, sel):
        if name == "group":
            if sel is None:
                return self.currentGroup
            else:
                return self.groupMap.get(sel)
        elif name == "layout":
            if sel is None:
                return self.currentGroup.layout
            else:
                return utils.lget(self.currentGroup.layouts, sel)
        elif name == "widget":
            return self.widgetMap.get(sel)
        elif name == "bar":
            return getattr(self.currentScreen, sel)
        elif name == "window":
            if sel is None:
                return self.currentWindow
            else:
                return self.clientFromWID(sel)
        elif name == "screen":
            if sel is None:
                return self.currentScreen
            else:
                return utils.lget(self.screens, sel)

    def listWID(self):
        return [i.window.wid for i in self.windowMap.values()]

    def clientFromWID(self, wid):
        for i in self.windowMap.values():
            if i.window.wid == wid:
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
        # FIXME: This needs to be done with sendevent, once we have that fixed.
        keysym = xcbq.keysyms.get(key)
        if keysym is None:
            raise command.CommandError("Unknown key: %s"%key)
        keycode = self.conn.first_sym_to_code[keysym]
        class DummyEv:
            pass

        d = DummyEv()
        d.detail = keycode
        try:
            d.state = utils.translateMasks(modifiers)
        except KeyError, v:
            return v.args[0]
        self.handle_KeyPress(d)

    def cmd_execute(self, cmd, args):
        """
            Executes the specified command, replacing the current process.
        """
        os.execv(cmd, args)

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
        self.conn.flush()

    def cmd_to_screen(self, n):
        """
            Warp to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return self.toScreen(n)

    def cmd_to_next_screen(self):
        """
            Move to next screen
        """
        return self.toScreen((self.screens.index(self.currentScreen) + 1 ) % len(self.screens))

    def cmd_to_prev_screen(self):
        """
            Move to the previous screen
        """
        return self.toScreen((self.screens.index(self.currentScreen) - 1) % len(self.screens))    

    def cmd_windows(self):
        """
            Return info for each client window.
        """
        return [i.info() for i in self.windowMap.values() if not isinstance(i, window.Internal)]

    def cmd_internal_windows(self):
        """
            Return info for each internal window (bars, for example).
        """
        return [i.info() for i in self.windowMap.values() if isinstance(i, window.Internal)]

    def cmd_info(self):
        """
            Returns a dictionary of info on the Qtile instance.
        """
        return dict(
            socketname = self.fname
        )
        return [i.info() for i in self.windowMap.values()]

    def cmd_shutdown(self):
        """
            Quit Qtile.
        """
        self._exit = True

    def cmd_spawncmd(self, prompt="spawn:", widget="prompt"):
        """
            Spawn a command using a prompt widget, with tab-completion. 

            prompt: Text with which to prompt user.
            widget: Name of the prompt widget (default: "prompt").
        """
        try:
            mb = self.widgetMap[widget]
            mb.startInput(prompt, self.cmd_spawn, "cmd")
        except:
            self.log.add("No widget named '%s' present."%widget)

    def cmd_addgroup(self, group):
        return self.addGroup(group)

    def cmd_delgroup(self, group):
        return self.delGroup(group)


