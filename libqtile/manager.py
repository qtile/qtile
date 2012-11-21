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

from libqtile.log_utils import init_log
from xcb.xproto import EventMask
import atexit
import command
import contextlib
import gobject
import hook
import logging
import os
import os.path
import sys
import traceback
import utils
import window
import xcb
import xcb.xinerama
import xcb.xproto
import xcbq


class QtileError(Exception):
    pass


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
            raise QtileError("Unknown key: %s" % key)
        self.keysym = xcbq.keysyms[key]
        try:
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise QtileError(v)

    def __repr__(self):
        return "Key(%s, %s)" % (self.modifiers, self.key)


class Drag(object):
    """
        Defines binding of a mouse to some dragging action

        On each motion event command is executed
        with two extra parameters added
        x and y offset from previous move
    """
    def __init__(self, modifiers, button, *commands, **kw):
        self.start = kw.pop('start', None)
        if kw:
            raise TypeError("Unexpected arguments: %s" % ', '.join(kw))
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise QtileError(v)

    def __repr__(self):
        return "Drag(%s, %s)" % (self.modifiers, self.button)


class Click(object):
    """
        Defines binding of a mouse click
    """
    def __init__(self, modifiers, button, *commands):
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise QtileError(v)

    def __repr__(self):
        return "Click(%s, %s)" % (self.modifiers, self.button)


class ScreenRect(object):

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s %d,%d %d,%d>' % (self.__class__.__name__,
            self.x, self.y, self.width, self.height)

    def hsplit(self, columnwidth):
        assert columnwidth > 0
        assert columnwidth < self.width
        return (self.__class__(self.x, self.y, columnwidth, self.height),
                self.__class__(self.x + columnwidth, self.y,
                               self.width - columnwidth, self.height))

    def vsplit(self, rowheight):
        assert rowheight > 0
        assert rowheight < self.height
        return (self.__class__(self.x, self.y, self.width, rowheight),
                self.__class__(self.x, self.y + rowheight,
                               self.width, self.height - rowheight))


class Screen(command.CommandObject):
    """
        A physical screen, and its associated paraphernalia.
    """
    group = None

    def __init__(self, top=None, bottom=None, left=None, right=None,
                 x=None, y=None, width=None, height=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.

            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).

            x,y,width and height aren't specified usually unless you are
            using 'fake screens'.
        """
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right
        self.qtile = None
        self.index = None
        self.x = x  # x position of upper left corner can be > 0
                    # if one screen is "right" of the other
        self.y = y
        self.width = width
        self.height = height

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

    def get_rect(self):
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def setGroup(self, new_group):
        """
        Put group on this screen
        """
        if new_group.screen == self:
            return
        elif new_group.screen:
            # g1 <-> s1 (self)
            # g2 (new_group)<-> s2 to
            # g1 <-> s2
            # g2 <-> s1
            g1 = self.group
            s1 = self
            g2 = new_group
            s2 = new_group.screen

            s2.group = g1
            g1._setScreen(s2)
            s1.group = g2
            g2._setScreen(s1)
        else:
            if self.group is not None:
                self.group._setScreen(None)
            self.group = new_group
            new_group._setScreen(self)
        hook.fire("setgroup")
        hook.fire("focus_change")
        hook.fire("layout_change",
                  self.group.layouts[self.group.currentLayout],
                  self.group)

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
            Returns a dictionary of info for this screen.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x=self.x,
            y=self.y
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
        self.windows = set()
        self.qtile = None
        self.layouts = []
        self.floating_layout = None
        self.currentWindow = None
        self.screen = None
        self.currentLayout = None

    def _configure(self, layouts, floating_layout, qtile):
        self.screen = None
        self.currentLayout = 0
        self.currentWindow = None
        self.windows = set()
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        self.floating_layout = floating_layout.clone(self)
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
                hook.fire("layout_change",
                          self.layouts[self.currentLayout], self)
                self.layoutAll()
                return
        raise ValueError("No such layout: %s" % layout)

    def nextLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout + 1) % (len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout], self)
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def prevLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout - 1) % (len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout], self)
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def layoutAll(self, warp=False):
        """
        Layout the floating layer, then the current layout.

        If we have have a currentWindow give it focus, optionally
        moving warp to it.
        """
        if self.screen and len(self.windows):
            with self.disableMask(xcb.xproto.EventMask.EnterWindow):
                normal = [x for x in self.windows if not x.floating]
                floating = [x for x in self.windows
                    if x.floating and not x.minimized]
                screen = self.screen.get_rect()
                if normal:
                    self.layout.layout(normal, screen)
                if floating:
                    self.floating_layout.layout(floating, screen)
                if (self.currentWindow and
                    self.screen == self.qtile.currentScreen):
                    self.currentWindow.focus(warp)

    def _setScreen(self, screen):
        """
        Set this group's screen to new_screen
        """
        if screen == self.screen:
            return
        self.screen = screen
        if self.screen:
            # move all floating guys offset to new screen
            self.floating_layout.to_screen(self.screen)
            self.layoutAll()
            rect = self.screen.get_rect()
            self.floating_layout.show(rect)
            self.layout.show(rect)
        else:
            self.hide()

    def hide(self):
        self.screen = None
        with self.disableMask(xcb.xproto.EventMask.EnterWindow |
                              xcb.xproto.EventMask.FocusChange |
                              xcb.xproto.EventMask.LeaveWindow):
            for i in self.windows:
                i.hide()
            self.layout.hide()

    @contextlib.contextmanager
    def disableMask(self, mask):
        for i in self.windows:
            i._disableMask(mask)
        yield
        for i in self.windows:
            i._resetMask()

    def focus(self, win, warp):
        """
            if win is in the group, blur any windows and call
            ``focus`` on the layout (in case it wants to track
            anything), fire focus_change hook and invoke layoutAll.

            warp - warp pointer to win
        """
        if self.qtile._drag:
            # don't change focus while dragging windows
            return
        if win and not win in self.windows:
            return
        if win:
            self.currentWindow = win
            if win.floating:
                for l in self.layouts:
                    l.blur()
                self.floating_layout.focus(win)
            else:
                self.floating_layout.blur()
                for l in self.layouts:
                    l.focus(win)
        else:
            self.currentWindow = None
        hook.fire("focus_change")
        # !!! note that warp isn't hooked up now
        self.layoutAll(warp)

    def info(self):
        return dict(
            name=self.name,
            focus=self.currentWindow.name if self.currentWindow else None,
            windows=[i.name for i in self.windows],
            layout=self.layout.name,
            floating_info=self.floating_layout.info(),
            screen=self.screen.index if self.screen else None
        )

    def add(self, win):
        hook.fire("group_window_add")
        self.windows.add(win)
        win.group = self
        try:
            if (win.window.get_net_wm_state() == 'fullscreen' and
                self.qtile.config.auto_fullscreen):
                win._float_state = window.FULLSCREEN
            elif self.floating_layout.match(win):
                # !!! tell it to float, can't set floating
                # because it's too early
                # so just set the flag underneath
                win._float_state = window.FLOATING
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            pass  # doesn't matter
        if win.floating:
            self.floating_layout.add(win)
        else:
            for i in self.layouts:
                i.add(win)
        self.focus(win, True)

    def remove(self, win):
        self.windows.remove(win)
        win.group = None
        nextfocus = None
        if win.floating:
            nextfocus = self.floating_layout.remove(win)
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
        else:
            for i in self.layouts:
                if i is self.layout:
                    nextfocus = i.remove(win)
                else:
                    i.remove(win)
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
        self.focus(nextfocus, True)
        #else: TODO: change focus

    def mark_floating(self, win, floating):
        if floating and win in self.floating_layout.clients:
            # already floating
            pass
        elif floating:
            for i in self.layouts:
                i.remove(win)
                if win is self.currentWindow:
                    i.blur()
            self.floating_layout.add(win)
            if win is self.currentWindow:
                self.floating_layout.focus(win)
        else:
            self.floating_layout.remove(win)
            self.floating_layout.blur()
            for i in self.layouts:
                i.add(win)
                if win is self.currentWindow:
                    i.focus(win)
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
            Returns a dictionary of info for this group.
        """
        return self.info()

    def cmd_toscreen(self, screen=None):
        """
            Pull a group to a specified screen.

            - screen: Screen offset. If not specified,
                      we assume the current screen.

            Pull group to the current screen:
                toscreen()

            Pull group to screen 0:
                toscreen(0)
        """
        if screen is None:
            screen = self.qtile.currentScreen
        else:
            screen = self.qtile.screens[screen]
        screen.setGroup(self)

    def _dirGroup(self, direction):
        currentgroup = self.qtile.groups.index(self)
        nextgroup = (currentgroup + direction) % len(self.qtile.groups)
        return self.qtile.groups[nextgroup]

    def _dirSkipEmptyGroup(self, direction):
        """
        Find a non-empty group walking the groups list in the specified
        direction.
        """
        index = currentgroup = self.qtile.groups.index(self)
        while True:
            index = (index + direction) % len(self.qtile.groups)
            group = self.qtile.groups[index]
            if index == currentgroup or group.windows:
                return group

    def prevGroup(self):
        return self._dirGroup(-1)

    def nextGroup(self):
        return self._dirGroup(1)

    def prevEmptyGroup(self):
        return self._dirSkipEmptyGroup(-1)

    def nextEmptyGroup(self):
        return self._dirSkipEmptyGroup(1)

    # FIXME cmd_nextgroup and cmd_prevgroup should be on the Screen object.
    def cmd_nextgroup(self, skip_empty=False):
        """
            Switch to the next group.
        """
        if skip_empty:
            n = self.nextEmptyGroup()
        else:
            n = self.nextGroup()
        self.qtile.currentScreen.setGroup(n)
        return n.name

    def cmd_prevgroup(self, skip_empty=False):
        """
            Switch to the previous group.
        """
        if skip_empty:
            n = self.prevEmptyGroup()
        else:
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

    def cmd_next_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_next(self.currentWindow)
            if not nxt:
                nxt = self.layout.focus_first()
            if not nxt:
                nxt = self.floating_layout.focus_first()
        else:
            nxt = self.layout.focus_next(self.currentWindow)
            if not nxt:
                nxt = self.floating_layout.focus_first()
            if not nxt:
                nxt = self.layout.focus_first()
        self.focus(nxt, True)

    def cmd_prev_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_prev(self.currentWindow)
            if not nxt:
                nxt = self.layout.focus_last()
            if not nxt:
                nxt = self.floating_layout.focus_last()
        else:
            nxt = self.layout.focus_prev(self.currentWindow)
            if not nxt:
                nxt = self.floating_layout.focus_last()
            if not nxt:
                nxt = self.layout.focus_last()
        self.focus(nxt, True)

    def cmd_switch_groups(self, name):
        """
            Switch position of current group with name
        """
        self.qtile.cmd_switch_groups(self.name, name)


class Qtile(command.CommandObject):
    """
        This object is the __root__ of the command graph.
    """
    _exit = False
    _abort = False

    def __init__(self, config,
                 displayName=None, fname=None, no_spawn=False, log=None):
        if log == None:
            log = init_log()
        self.log = log
        self.no_spawn = no_spawn
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
        hook.init(self)

        self.keyMap = {}
        self.windowMap = {}
        self.widgetMap = {}
        self.groupMap = {}
        self.groups = []
        self.keyMap = {}

        # Find the modifier mask for the numlock key, if there is one:
        nc = self.conn.keysym_to_keycode(xcbq.keysyms["Num_Lock"])
        self.numlockMask = xcbq.ModMasks[self.conn.get_modifier(nc)]
        self.validMask = ~(self.numlockMask | xcbq.ModMasks["lock"])

        # Because we only do Xinerama multi-screening,
        # we can assume that the first
        # screen's root is _the_ root.
        self.root = self.conn.default_screen.root
        self.root.set_attribute(
            eventmask=(
                EventMask.StructureNotify |
                EventMask.SubstructureNotify |
                EventMask.SubstructureRedirect |
                EventMask.EnterWindow |
                EventMask.LeaveWindow)
        )

        if config.main:
            config.main(self)

        self.groups += self.config.groups[:]

        for i in self.groups:
            i._configure(config.layouts, config.floating_layout, self)
            self.groupMap[i.name] = i

        self.currentScreen = None
        self.screens = []
        self._process_screens()
        self.currentScreen = self.screens[0]
        self._drag = None

        self.ignoreEvents = set([
            xcb.xproto.KeyReleaseEvent,
            xcb.xproto.ReparentNotifyEvent,
            xcb.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcb.xproto.MapNotifyEvent,
            xcb.xproto.LeaveNotifyEvent,
            xcb.xproto.FocusOutEvent,
            xcb.xproto.FocusInEvent,
            xcb.xproto.NoExposureEvent
        ])

        self.conn.flush()
        self.conn.xsync()
        self._xpoll()
        if self._abort:
            self.log.error(
                "Access denied: "
                "Another window manager running?")
            sys.exit(1)

        self.server = command._Server(self.fname, self, config)

        # Map and Grab keys
        for key in self.config.keys:
            self.mapKey(key)

        self.mouseMap = {}
        for i in self.config.mouse:
            self.mouseMap[i.button_code] = i

        self.grabMouse()

        hook.fire("startup")

        self.scan()
        self.update_net_desktops()
        hook.subscribe.setgroup(self.update_net_desktops)

    def _process_fake_screens(self):
        """
        Since Xephyr, Xnest don't really support offset screens,
        we'll fake it here for testing, (or if you want to partition
        a physical monitor into separate screens)
        """
        for i, s in enumerate(self.config.fake_screens):
            # should have x,y, width and height set
            s._configure(self, i, s.x, s.y, s.width, s.height, self.groups[i])
            if not self.currentScreen:
                self.currentScreen = s
            self.screens.append(s)

    def _process_screens(self):
        if hasattr(self.config, 'fake_screens'):
            self._process_fake_screens()
            return
        for i, s in enumerate(self.conn.pseudoscreens):
            if i + 1 > len(self.config.screens):
                scr = Screen()
            else:
                scr = self.config.screens[i]
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
            if self.config.screens:
                s = self.config.screens[0]
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

    def mapKey(self, key):
        self.keyMap[(key.keysym, key.modmask & self.validMask)] = key
        code = self.conn.keysym_to_keycode(key.keysym)
        self.root.grab_key(
            code,
            key.modmask,
            True,
            xcb.xproto.GrabMode.Async,
            xcb.xproto.GrabMode.Async,
        )
        if self.numlockMask:
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask,
                True,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
            )
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask | xcbq.ModMasks["lock"],
                True,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
            )

    def unmapKey(self, key):
        key_index = (key.keysym, key.modmask & self.validMask)
        if not key_index in self.keyMap:
            return

        code = self.conn.keysym_to_keycode(key.keysym)
        self.root.ungrab_key(
            code,
            key.modmask)
        if self.numlockMask:
            self.root.ungrab_key(
                code,
                key.modmask | self.numlockMask
            )
            self.root.ungrab_key(
                code,
                key.modmask | self.numlockMask | xcbq.ModMasks["lock"]
            )
        del(self.keyMap[key_index])

    def update_net_desktops(self):
        try:
            index = self.groups.index(self.currentGroup)
        except:
            index = 0

        self.root.set_property("_NET_NUMBER_OF_DESKTOPS", len(self.groups))
        self.root.set_property("_NET_DESKTOP_NAMES", "\0".join(
                [i.name for i in self.groups])
            )
        self.root.set_property("_NET_CURRENT_DESKTOP", index)

    def addGroup(self, name):
        if name not in self.groupMap.keys():
            g = Group(name)
            self.groups.append(g)
            g._configure(
                self.config.layouts, self.config.floating_layout, self)
            self.groupMap[name] = g
            hook.fire("addgroup")
            self.update_net_desktops()

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
            self.update_net_desktops()


    def registerWidget(self, w):
        """
            Register a bar widget. If a widget with the same name already
            exists, this raises a ConfigError.
        """
        if w.name:
            if w.name in self.widgetMap:
                return
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
        for item in children:
            try:
                attrs = item.get_attributes()
                state = item.get_wm_state()
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                continue

            if attrs and attrs.map_state == xcb.xproto.MapState.Unmapped:
                continue
            if state and state[0] == window.WithdrawnState:
                continue
            self.manage(item)

    def unmanage(self, win):
        c = self.windowMap.get(win)
        if c:
            hook.fire("client_killed", c)
            if getattr(c, "group", None):
                c.window.unmap()
                c.state = window.WithdrawnState
                c.group.remove(c)
            del self.windowMap[win]

    def manage(self, w):
        try:
            attrs = w.get_attributes()
            internal = w.get_property("QTILE_INTERNAL")
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return
        if attrs and attrs.override_redirect:
            return

        if not w.wid in self.windowMap:
            if internal:
                try:
                    c = window.Internal(w, self)
                except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                    return
                self.windowMap[w.wid] = c
            else:
                try:
                    c = window.Window(w, self)
                except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                    return
                hook.fire("client_new", c)
                # Window may be defunct because
                # it's been declared static in hook.
                if c.defunct:
                    return
                self.windowMap[w.wid] = c
                # Window may have been bound to a group in the hook.
                if not c.group:
                    self.currentScreen.group.add(c)
                hook.fire("client_managed", c)
            return c
        else:
            return self.windowMap[w.wid]

    def grabMouse(self):
        self.root.ungrab_button(None, None)
        for i in self.config.mouse:
            eventmask = EventMask.ButtonPress
            if isinstance(i, Drag):
                eventmask |= EventMask.ButtonRelease
            self.root.grab_button(
                i.button_code,
                i.modmask,
                True,
                eventmask,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
                )
            if self.numlockMask:
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask,
                    True,
                    eventmask,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                    )
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask | xcbq.ModMasks["lock"],
                    True,
                    eventmask,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                    )

    def grabKeys(self):
        self.root.ungrab_key(None, None)
        for key in self.keyMap.values():
            self.mapKey(key)

    def get_target_chain(self, ename, e):
        """
            Returns a chain of targets that can handle this event. The event
            will be passed to each target in turn for handling, until one of
            the handlers returns False or the end of the chain is reached.
        """
        chain = []
        handler = "handle_%s" % ename
        # Certain events expose the affected window id as an "event" attribute.
        eventEvents = [
            "EnterNotify",
            "ButtonPress",
            "ButtonRelease",
            "KeyPress",
        ]
        c = None
        if hasattr(e, "window"):
            c = self.windowMap.get(e.window)
        elif hasattr(e, "drawable"):
            c = self.windowMap.get(e.drawable)
        elif ename in eventEvents:
            c = self.windowMap.get(e.event)

        if c and hasattr(c, handler):
            chain.append(getattr(c, handler))
        if hasattr(self, handler):
            chain.append(getattr(self, handler))
        if not chain:
            self.log.info("Unknown event: %r" % ename)
        return chain

    def _xpoll(self, conn=None, cond=None):
        while True:
            try:
                e = self.conn.conn.poll_for_event()
                if not e:
                    break
                # This should be done in xpyb
                # client mesages start at 128
                if e.response_type >= 128:
                    e = xcb.xproto.ClientMessageEvent(e)

                ename = e.__class__.__name__

                if ename.endswith("Event"):
                    ename = ename[:-5]
                self.log.debug(ename)
                if not e.__class__ in self.ignoreEvents:
                    for h in self.get_target_chain(ename, e):
                        self.log.info("Handling: %s" % ename)
                        r = h(e)
                        if not r:
                            break
            except Exception:
                self.log.exception('Got an exception in poll loop')
                self._abort = True
                return False
        return True

    def loop(self):

        self.server.start()
        self.log.info('Adding io watch')
        display_tag = gobject.io_add_watch(
            self.conn.conn.get_file_descriptor(),
            gobject.IO_IN, self._xpoll)
        try:
            context = gobject.main_context_default()
            while True:
                if context.iteration(True):
                    try:
                        # this seems to be crucial part
                        self.conn.flush()

                    # Catch some bad X exceptions. Since X is event based, race
                    # conditions can occur almost anywhere in the code. For
                    # example, if a window is created and then immediately
                    # destroyed (before the event handler is evoked), when the
                    # event handler tries to examine the window properties, it
                    # will throw a BadWindow exception. We can essentially
                    # ignore it, since the window is already dead and we've got
                    # another event in the queue notifying us to clean it up.
                    except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                        # TODO: add some logging for this?
                        pass
                if self._exit:
                    self.log.info('Got shutdown, Breaking main loop cleanly')
                    break
                if self._abort:
                    self.log.warn('Got exception, Breaking main loop')
                    sys.exit(2)
        finally:
            self.log.info('Removing source')
            gobject.source_remove(display_tag)

    def find_screen(self, x, y):
        """
            Find a screen based on the x and y offset.
        """
        result = []
        for i in self.screens:
            if (x >= i.x and x <= i.x + i.width and
                y >= i.y and y <= i.y + i.height):
                result.append(i)
        if len(result) == 1:
            return result[0]
        return None

    def find_closest_screen(self, x, y):
        """
        If find_screen returns None, then this basically extends a
        screen vertically and horizontally and see if x,y lies in the
        band.

        Only works if it can find a SINGLE closest screen, else we
        revert to _find_closest_closest.

        Useful when dragging a window out of a screen onto another but
        having leftmost corner above viewport.
        """
        normal = self.find_screen(x, y)
        if normal is not None:
            return normal
        x_match = []
        y_match = []
        for i in self.screens:
            if x >= i.x and x <= i.x + i.width:
                x_match.append(i)
            if y >= i.y and y <= i.y + i.height:
                y_match.append(i)
        if len(x_match) == 1:
            return x_match[0]
        if len(y_match) == 1:
            return y_match[0]
        return self._find_closest_closest(x, y, x_match + y_match)

    def _find_closest_closest(self, x, y, candidate_screens):
        """
        if find_closest_screen can't determine one, we've got multiple
        screens, so figure out who is closer.  We'll calculate using
        the square of the distance from the center of a screen.

        Note that this could return None if x, y is right/below all
        screens (shouldn't happen but we don't do anything about it
        here other than returning None)
        """
        closest_distance = None
        closest_screen = None
        if not candidate_screens:
            # try all screens
            candidate_screens = self.screens
        # if left corner is below and right of screen
        # it can't really be a candidate
        candidate_screens = [s for s in candidate_screens
                             if x < s.x + s.width and y < s.y + s.width]
        for s in candidate_screens:
            middle_x = s.x + s.width / 2
            middle_y = s.y + s.height / 2
            distance = (x - middle_x) ** 2 + (y - middle_y) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_screen = s
        return closest_screen

    def handle_EnterNotify(self, e):
        if e.event in self.windowMap:
            return True
        s = self.find_screen(e.root_x, e.root_y)
        if s:
            self.toScreen(s.index)

    def handle_ClientMessage(self, event):
        atoms = self.conn.atoms

        opcode = xcb.xproto.ClientMessageData(event, 0, 20).data32[2]
        data = xcb.xproto.ClientMessageData(event, 12, 20)

        # handle change of desktop
        if atoms["_NET_CURRENT_DESKTOP"] == opcode:
            index = data.data32[0]
            try:
                self.currentScreen.setGroup(self.groups[index])
            except IndexError:
                self.log.info("Invalid Desktop Index: %s" % index)

    def handle_KeyPress(self, e):
        keysym = self.conn.code_to_syms[e.detail][0]
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask
        k = self.keyMap.get((keysym, state & self.validMask))
        if not k:
            self.log.info("Ignoring unknown keysym: %s" % keysym)
            return
        for i in k.commands:
            if i.check(self):
                status, val = self.server.call(
                    (i.selectors, i.name, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    self.log.error("KB command error %s: %s" % (i.name, val))
        else:
            return

    def handle_ButtonPress(self, e):
        button_code = e.detail
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask

        m = self.mouseMap.get(button_code)
        if not m or m.modmask & self.validMask != state & self.validMask:
            self.log.info("Ignoring unknown button: %s" % button_code)
            return
        if isinstance(m, Click):
            for i in m.commands:
                if i.check(self):
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args, i.kwargs))
                    if status in (command.ERROR, command.EXCEPTION):
                        self.log.error(
                            "Mouse command error %s: %s" % (i.name, val))
        elif isinstance(m, Drag):
            x = e.event_x
            y = e.event_y
            if m.start:
                i = m.start
                status, val = self.server.call(
                    (i.selectors, i.name, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    self.log.error(
                        "Mouse command error %s: %s" % (i.name, val))
                    return
            else:
                val = 0, 0
            self._drag = x, y, val[0], val[1], m.commands
            self.root.grab_pointer(
                True,
                xcbq.ButtonMotionMask |
                xcbq.AllButtonsMask |
                xcbq.ButtonReleaseMask,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
                )

    def handle_ButtonRelease(self, e):
        button_code = e.detail
        state = e.state & ~xcbq.AllButtonsMask
        if self.numlockMask:
            state = state | self.numlockMask
        m = self.mouseMap.get(button_code)
        if not m:
            self.log.info(
                "Ignoring unknown button release: %s" % button_code)
            return
        if isinstance(m, Drag):
            self._drag = None
            self.root.ungrab_pointer()

    def handle_MotionNotify(self, e):
        if self._drag is None:
            return
        ox, oy, rx, ry, cmd = self._drag
        dx = e.event_x - ox
        dy = e.event_y - oy
        if dx or dy:
            for i in cmd:
                if i.check(self):
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args +
                         (rx + dx, ry + dy), i.kwargs))
                    if status in (command.ERROR, command.EXCEPTION):
                        self.log.error(
                            "Mouse command error %s: %s" % (i.name, val))

    def handle_ConfigureNotify(self, e):
        """
            Handle xrandr events.
        """
        screen = self.currentScreen
        if (e.window == self.root.wid and
            e.width != screen.width and e.height != screen.height):
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
        if c and (not c.group or not c.group.screen):
            return
        w.map()

    def handle_DestroyNotify(self, e):
        self.unmanage(e.window)

    def handle_UnmapNotify(self, e):
        if e.event != self.root.wid:
            self.unmanage(e.window)

    def toScreen(self, n):
        """
        Have Qtile move to screen and put focus there
        """
        if len(self.screens) < n - 1:
            return
        self.currentScreen = self.screens[n]
        self.currentGroup.focus(
            self.currentWindow,
            True
        )

    def moveToGroup(self, group):
        """
            Create a group if it dosn't exist and move a windows there
        """
        if self.currentWindow and group:
            self.addGroup(group)
            self.currentWindow.togroup(group)

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
        """Set log level to DEBUG"""
        self.log.setLevel(logging.DEBUG)
        self.log.debug('Switching to DEBUG threshold')

    def cmd_info(self):
        """Set log level to INFO"""
        self.log.setLevel(logging.INFO)
        self.log.info('Switching to INFO threshold')

    def cmd_warning(self):
        """Set log level to WARNING"""
        self.log.setLevel(logging.WARNING)
        self.log.warning('Switching to WARNING threshold')

    def cmd_error(self):
        """Set log level to ERROR"""
        self.log.setLevel(logging.ERROR)
        self.log.error('Switching to ERROR threshold')

    def cmd_critical(self):
        """Set log level to CRITICAL"""
        self.log.setLevel(logging.CRITICAL)
        self.log.critical('Switching to CRITICAL threshold')

    def cmd_pause(self):
        """Drops into pdb"""
        import pdb
        pdb.set_trace()

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

    def cmd_prevlayout(self, group=None):
        """
            Switch to the prev layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groupMap.get(group)
        else:
            group = self.currentGroup
        group.prevLayout()

    def cmd_screens(self):
        """
            Return a list of dictionaries providing information on all screens.
        """
        lst = []
        for i in self.screens:
            lst.append(dict(
                index=i.index,
                group=i.group.name if i.group is not None else None,
                x=i.x,
                y=i.y,
                width=i.width,
                height=i.height,
                gaps=dict(
                    top=i.top.geometry() if i.top else None,
                    bottom=i.bottom.geometry() if i.bottom else None,
                    left=i.left.geometry() if i.left else None,
                    right=i.right.geometry() if i.right else None,
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
            raise command.CommandError("Unknown key: %s" % key)
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
        atexit._run_exitfuncs()
        os.execv(cmd, args)

    def cmd_restart(self):
        """
            Restart qtile using the execute command.
        """
        argv = [sys.executable] + sys.argv
        if '--no-spawn' not in argv:
            argv.append('--no-spawn')
        self.cmd_execute(sys.executable, argv)

    def cmd_spawn(self, cmd):
        """
            Run cmd in a shell.

            Example:

                spawn("firefox")
        """
        gobject.spawn_async([os.environ['SHELL'], '-c', cmd])

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
            Warp focus to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return self.toScreen(n)

    def cmd_to_next_screen(self):
        """
            Move to next screen
        """
        return self.toScreen(
            (self.screens.index(self.currentScreen) + 1) % len(self.screens))

    def cmd_to_prev_screen(self):
        """
            Move to the previous screen
        """
        return self.toScreen(
            (self.screens.index(self.currentScreen) - 1) % len(self.screens))

    def cmd_windows(self):
        """
            Return info for each client window.
        """
        return [i.info() for i in self.windowMap.values()
                if not isinstance(i, window.Internal)]

    def cmd_internal_windows(self):
        """
            Return info for each internal window (bars, for example).
        """
        return [i.info() for i in self.windowMap.values()
                if isinstance(i, window.Internal)]

    def cmd_qtile_info(self):
        """
            Returns a dictionary of info on the Qtile instance.
        """
        return dict(
            socketname=self.fname
        )

    def cmd_shutdown(self):
        """
            Quit Qtile.
        """
        self._exit = True

    def cmd_switch_groups(self, groupa, groupb):
        """
            Switch position of groupa to groupb
        """
        if groupa not in self.groupMap or groupb not in self.groupMap:
            return

        indexa = self.groups.index(self.groupMap[groupa])
        indexb = self.groups.index(self.groupMap[groupb])

        self.groups[indexa], self.groups[indexb] = \
                self.groups[indexb], self.groups[indexa]
        hook.fire("setgroup")
        self.update_net_desktops()

        # update window _NET_WM_DESKTOP
        for group in (self.groups[indexa], self.groups[indexb]):
            for window in group.windows:
                window.group = group

    def cmd_togroup(self, prompt="group: ", widget="prompt"):
        """
            Move current window to the selected group in a propmt widget

            prompt: Text with which to prompt user.
            widget: Name of the prompt widget (default: "prompt").
        """
        if not self.currentWindow:
            self.log.warning("No window to move")
            return

        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.error("No widget named '%s' present." % widget)
            return

        mb.startInput(prompt, self.moveToGroup, "group")

    def cmd_switchgroup(self, prompt="group: ", widget="prompt"):
        def f(group):
            if group:
                try:
                    self.groupMap[group].cmd_toscreen()
                except KeyError:
                    self.log.add("No group named '%s' present." % group)
                    pass

        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.add("No widget named '%s' present." % widget)
            return

        mb.startInput(prompt, f, "group")

    def cmd_spawncmd(self, prompt="spawn: ", widget="prompt",
                     command="%s", complete="cmd"):
        """
            Spawn a command using a prompt widget, with tab-completion.

            prompt: Text with which to prompt user (default: "spawn: ").
            widget: Name of the prompt widget (default: "prompt").
            command: command template (default: "%s").
            complete: Tab completion function (default: "cmd")
        """
        def f(args):
            if args:
                self.cmd_spawn(command % args)
        try:
            mb = self.widgetMap[widget]
            mb.startInput(prompt, f, complete)
        except:
            self.log.error("No widget named '%s' present."%widget)

    def cmd_qtilecmd(self, prompt="command: ",
                     widget="prompt", messenger="xmessage"):
        """
            Execute a Qtile command using the client syntax.
            Tab completeion aids navigation of the command tree.

            prompt: Text to display at the prompt (default: "command: ").
            widget: Name of the prompt widget (default: "prompt").
            messenger: command to display output (default: "xmessage").
                Set this to None to disable.
        """
        def f(cmd):
            if cmd:
                c = command.CommandRoot(self)
                try:
                   cmd_arg = str(cmd).split(' ')
                except AttributeError:
                    return
                cmd_len = len(cmd_arg)
                if cmd_len == 0:
                    self.log.info('No command entered.')
                    return
                try:
                    result = eval('c.%s' % (cmd))
                except (
                        command.CommandError,
                        command.CommandException,
                        AttributeError) as err:
                    self.log.error(err.message)
                    result = None
                if result != None:
                    from pprint import pformat
                    message = pformat(result)
                    if messenger:
                        self.cmd_spawn('%s "%s"' % (messenger, message))
                    self.log.info(result)

        mb = self.widgetMap[widget]
        if not mb:
            self.log.error("No widget named %s present." % widget)
            return
        mb.startInput(prompt, f, "qsh")

    def cmd_addgroup(self, group):
        return self.addGroup(group)

    def cmd_delgroup(self, group):
        return self.delGroup(group)

    def cmd_eval(self, code):
        """
            Evaluates code in the same context as this function.
            Return value is (success, result), success being a boolean and
            result being a string representing the return value of eval, or
            None if exec was used instead.
        """
        try:
            try:
                return (True, str(eval(code)))
            except SyntaxError:
                exec code
                return (True, None)
        except:
            error = traceback.format_exc().strip().split("\n")[-1]
            return (False, error)

    def cmd_function(self, function):
        """ Call a function with qtile instance as argument """
        try:
            function(self)
        except Exception:
            error = traceback.format_exc().strip().split("\n")[-1]
            self.log.error('Can\'t call "%s": %s' % (function, error))
