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
import datetime, subprocess, sys, operator, os, traceback, shlex
import select
import xcbq
import xcb.xproto, xcb.xinerama
import xcb
from xcb.xproto import EventMask
import command, utils, window, confreader, hook, xk

import Xlib
import Xlib.display
import Xlib.ext.xinerama as xinerama
from Xlib import X
import Xlib.protocol.event as event

class QtileError(Exception): pass
class ThemeSyntaxError(Exception): pass


class Core:
    def __init__(self):
        pass


class Key:
    def __init__(self, modifiers, key, *commands):
        """
            :modifiers A list of modifier specifications. Modifier
            specifications are one of: "shift", "lock", "control", "mod1",
            "mod2", "mod3", "mod4", "mod5".
            :key A key specification, e.g. "a", "Tab", "Return", "space".
            :*commands A list of lazy command objects generated with the
            command.lazy helper. If multiple Call objects are specified, they
            are run in sequence.
        """
        self.modifiers, self.key, self.commands = modifiers, key, commands
        self.keysym = xk.string_to_keysym(key)
        if self.keysym == 0:
            raise QtileError("Unknown key: %s"%key)
        try:
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise QtileError(v)
    
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

    def _configure(self, qtile, theme, index, x, y, width, height, group):
        self.qtile, self.theme = qtile, theme
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self, theme)

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
            return True, [i.window.id for i in self.group.windows]
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
                    if i.window.id == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.theme, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.resize()
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
            self.layout.layout(self.windows)
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
        hook.fire("window_add")
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
            return True, [i.window.id for i in self.windows]
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
                    if i.window.id == sel:
                        return i
        elif name == "screen":
            return self.screen

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
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
    
    def move_groups(self, direction):
        currentgroup = self.qtile.groups.index(self)
        nextgroup = (currentgroup + direction) % len(self.qtile.groups)
        self.qtile.currentScreen.setGroup(self.qtile.groups[nextgroup])

    def cmd_nextgroup(self):
        self.move_groups(1)

    def cmd_prevgroup(self):
        self.move_groups(-1)

    def cmd_unminimise_all(self):
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


class Theme(object):
    """
        Themes are a way to collect generic, commonly used graphical hints
        together in one place. 
    """
    # The type specification should be extended to contain types like "colour".
    _elements = {
        'fg_normal':            ('#ffffff', "string"),
        'fg_focus':             ('#ff0000', "string"),
        'fg_active':            ('#990000', "string"),
        'fg_urgent':            ('#000000', "string"),
        'bg_normal':            ('#000000', "string"),
        'bg_focus':             ('#ffffff', "string"),
        'bg_active':            ('#888888', "string"),
        'bg_urgent':            ('#ffff00', "string"),
        'border_normal':        ('#000000', "string"),
        'border_focus':         ('#0000ff', "string"),
        'border_active':        ('#ff0000', "string"),
        'border_urgent':        ('#ffff00', "string"),
        'border_width':         (1, "integer"),
        'font':                 ("none", "integer"),
        'opacity':              (1.0, "float"),
    }
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.children = {}
        self.values = {}
        self.path = None
        for k, v in kwargs.items():
            if k not in self._elements:
                raise ValueError("Unknown theme element: %s"%k)
            setattr(self, k, v)

    def __getattr__(self, key):
        if key in self._elements:
            if key in self.values:
                return self.values[key]
            elif self.parent:
                return self.parent.__getattr__(key)
            else:
                return self._elements[key][0]
        raise AttributeError("No such element: %s"%key)

    def __setattr__(self, key, value):
        if key in self._elements:
            self.values[key] = self._convert(key, value)
        else:
            object.__setattr__(self, key, value)

    def __setitem__(self, key, value):
        self.children[key] = value
        value.parent = self
        value.path = key if not self.path else self.path + "." + key

    def __getitem__(self, key):
        return self.get(key)

    def __repr__(self):
        return "Theme: %s"%(self.path or "default")

    def _get(self, parts):
        if not parts:
            return self
        else:
            return self.children[parts[0]]._get(parts[1:])

    def get(self, path):
        """
            Get a theme object matching a given path.
        """
        if not path:
            return self
        parts = path.split(".")
        try:
            return self._get(parts)
        except KeyError:
            raise KeyError("No such path: %s"%path)

    def addSection(self, path, d):
        parts = path.split()
        parent = self.get(".".join(parts[:-1]))
        parent[parts[-1]] = Theme(**d)

    def preOrder(self):
        """
            Traverse the tree in pre-order.
        """
        yield self
        for k, v in sorted(self.children.items()):
            for j in v.preOrder():
                yield j

    def dump(self):
        """
            Dump a parseable version of the theme. Include non-overridden
            defaults as comments.
        """
        s = []
        for e in self.preOrder():
            s.append("%s {"%(e.path or "default"))
            if not e.parent:
                for k in sorted(e._elements.keys()):
                    if k in e.values:
                        s.append("\t%s = %s"%(k, e.values[k]))
                    else:
                        s.append("\t#%s = %s"%(k, e._elements[k][0]))
            else:
                for k, v in sorted(e.values.items()):
                    s.append("\t%s = %s"%(k, v))
            s.append("}")
        return "\n".join(s)

    def __eq__(self, other):
        return self.dump() == other.dump()

    @classmethod
    def _convert(klass, name, value):
        if name not in klass._elements:
            raise ThemeSyntaxError("Not a valid theme element: %s"%name)
        t = klass._elements[name][1]
        try:
            if t == "integer":  return int(value)
            elif t == "float":  return float(value)
            elif t == "string": return str(value)
        except ValueError:
            raise ThemeSyntaxError("Theme element %s must be of type %s."%(name, t))

    @classmethod
    def parse(klass, s):
        """
            Parse a Theme specification string.
        """
        sections = {}
        lst = shlex.split(s, True)
        lst.reverse()
        while lst:
            name = lst.pop()
            elements = {}
            if not lst or lst.pop() != "{":
                raise ThemeSyntaxError("Syntax error in section: %s"%name)
            while True:
                if not lst:
                    raise ThemeSyntaxError("Syntax error in section: %s"%name)
                e = lst.pop()
                if e == "}":
                    break
                if not lst or lst.pop() != "=":
                    raise ThemeSyntaxError("Syntax error near: %s"%e)
                if not lst:
                    raise ThemeSyntaxError("Syntax error near: %s"%e)
                v = lst.pop()
                elements[e] = klass._convert(e, v)
            sections[name] = elements
        root = Theme(**sections.get("default", {}))
        for i in sorted(sections.keys()):
            if i == "default":
                continue
            root.addSection(i, sections[i])
        return root

    @classmethod
    def fromFile(klass, fname):
        """
            Construct a Theme tree from a file.
        """
        s = open(fname).read()
        return klass.parse(s)


class Qtile(command.CommandObject):
    debug = False
    _exit = False
    _testing = False
    _logLength = 100 
    def __init__(self, config, displayName=None, fname=None):
        if not displayName:
            displayName = os.environ.get("DISPLAY")
            if not displayName:
                raise QtileError("No DISPLAY set.")
        if not fname:
            if not "." in displayName:
                displayName = displayName + ".0"
            fname = os.path.join("~", command.SOCKBASE%displayName)
            fname = os.path.expanduser(fname)

        self.conn = xcbq.Connection(displayName)
        self.conn.grab_server()
        self.conn.flush()

        self.config, self.fname = config, fname
        self.log = Log(
                self._logLength,
                sys.stderr if self.debug else None
            )
        hook.init(self)

        self.windowMap = {}
        self.internalMap = {}
        self.widgetMap = {}
        self.groupMap = {}

        if config.theme:
            self.theme = config.theme
        else:
            self.theme = Theme()

        self.groups = []
        for i in self.config.groups:
            g = Group(i, self.config.layouts, self)
            self.groups.append(g)
            self.groupMap[g.name] = g

        self.currentScreen = None
        self.screens = []

        extensions = self.conn.extensions()
        if "xinerama" in extensions:
            for i, s in enumerate(self.conn.xinerama.query_screens()):
                if i+1 > len(config.screens):
                    scr = Screen()
                else:
                    scr = config.screens[i]
                if not self.currentScreen:
                    self.currentScreen = scr
                scr._configure(
                    self,
                    self.theme,
                    i,
                    s.x_org,
                    s.y_org,
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
                self, self.theme,
                0, 0, 0,
                self.conn.default_screen.width_in_pixels,
                self.conn.default_screen.height_in_pixels,
                self.groups[0],
            )
            self.screens.append(s)
        self.currentScreen = self.screens[0]

        #self.display.set_error_handler(self.initialErrorHandler)
        self.conn.screens[0].root.set_attribute(
            eventmask = EventMask.StructureNotify |\
                        EventMask.SubstructureNotify |\
                        EventMask.SubstructureRedirect |\
                        EventMask.EnterWindow |\
                        EventMask.LeaveWindow
        )
        self.conn.flush()
        if self._exit:
            print >> sys.stderr, "Access denied: Another window manager running?"
            sys.exit(1)
        # Now install the real error handler
        #self.display.set_error_handler(self.errorHandler)

        self.server = command._Server(self.fname, self, config)
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

        # Find the modifier mask for the numlock key, if there is one:
        maskmap = {
            X.ControlMapIndex: X.ControlMask,
            X.LockMapIndex: X.LockMask,
            X.Mod1MapIndex: X.Mod1Mask,
            X.Mod2MapIndex: X.Mod2Mask,
            X.Mod3MapIndex: X.Mod3Mask,
            X.Mod4MapIndex: X.Mod4Mask,
            X.Mod5MapIndex: X.Mod5Mask,
            X.ShiftMapIndex: X.ShiftMask,
        }
        nc = self.display.keysym_to_keycode(
                xk.string_to_keysym("Num_Lock")
            )
        self.numlockMask = None
        for i, l in enumerate(self.display.get_modifier_mapping()):
            for j in l:
                if j == nc:
                    self.numlockMask = maskmap[i]
        self.validMask = ~(self.numlockMask | X.LockMask)


        self.keyMap = {}
        for i in self.config.keys:
            self.keyMap[(i.keysym, i.modmask&self.validMask)] = i
        

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

    @utils.LRUCache(200)
    def colorPixel(self, name):
        colormap = self.display.screen().default_colormap
        return colormap.alloc_named_color(name).pixel

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
            hook.fire("client_killed", c)

    def manage(self, w):
        try:
            attrs = w.get_attributes()
            internal = w.get_full_property(self.atoms["internal"], self.atoms["python"])
        except Xlib.error.BadWindow:
            return
        if attrs and attrs.override_redirect:
            return
        if internal:
            if not w in self.internalMap:
                c = window.Internal(w, self)
                self.internalMap[w] = c
        else:
            if not w in self.windowMap:
                c = window.Window(w, self)
                self.windowMap[w] = c
                self.currentScreen.group.add(c)
                hook.fire("client_new", c)

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
            if self.numlockMask:
                self.root.grab_key(
                    code,
                    i.modmask | self.numlockMask,
                    True,
                    X.GrabModeAsync,
                    X.GrabModeAsync
                )
                self.root.grab_key(
                    code,
                    i.modmask | self.numlockMask | X.LockMask,
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
                                [], [], 0.01
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
        if e.window == self.root and e.width != screen.width and e.height != screen.height:
            screen.resize(0, 0, e.width, e.height)
            
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
        return [i.window.id for i in self.windowMap.values() + self.internalMap.values()]

    def clientFromWID(self, wid):
        all = self.windowMap.values() + self.internalMap.values()
        for i in all:
            if i.window.id == wid:
                return i
        return None

    def listThemes(self):
        names = os.listdir(self.config.themedir)
        ret = []
        for i in names:
            path = os.path.join(self.config.themedir, i)
            if os.path.isfile(path):
                ret.append(i)
        return sorted(ret)

    def loadTheme(self, name):
        themes = os.listdir(self.config.themedir)
        if not name in themes:
            raise QtileError("No such theme: %s"%name)
        self.config.theme = name
        self.theme = Theme.fromFile(os.path.join(self.config.themedir, name))
        # FIXME: Redraw layouts and bars here

    def cmd_themes(self):
        """
            Returns a list of available theme names.
        """
        return self.listThemes()

    def cmd_theme_load(self, name):
        """
            Loads a theme. Must be one of the list of available themes.
        """
        return self.loadTheme(name)

    def cmd_theme_next(self):
        """
            Load next theme.
        """
        themes = self.listThemes()
        if themes:
            if not self.config.theme:
                self.loadTheme(themes[0])
            elif self.config.theme in themes:
                offset = (themes.index(self.config.theme)+1)%len(themes)
                self.loadTheme(themes[offset])

    def cmd_theme_prev(self):
        """
            Load next theme.
        """
        themes = self.listThemes()
        if themes:
            if not self.config.theme:
                self.loadTheme(themes[-1])
            elif self.config.theme in themes:
                offset = (themes.index(self.config.theme)-1)%len(themes)
                self.loadTheme(themes[offset])

    def cmd_theme_current(self):
        """
            Returns the current theme name.
        """ 
        return self.config.theme

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
        keysym = xk.string_to_keysym(key)
        if keysym == 0:
            raise command.CommandError("Unknown key: %s"%key)
        keycode = self.display.keysym_to_keycode(keysym)
        try:
            mask = utils.translateMasks(modifiers)
        except KeyError, v:
            return v.args[0]
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
