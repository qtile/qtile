# vim: tabstop=4 shiftwidth=4 expandtab
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
from libqtile.dgroups import DGroups
from xcffib.xproto import EventMask, WindowError, AccessError, DrawableError
from xcffib import ConnectionException
import imp
import logging
import os
import os.path
import pickle
import shlex
import signal
import sys
import traceback
import xcffib
import xcffib.xinerama
import xcffib.xproto
import six

from six.moves import asyncio

from .config import Drag, Click, Screen, Match, Rule
from .group import _Group
from .state import QtileState
from .utils import QtileError
from .widget.base import _Widget
from . import command
from . import hook
from . import utils
from . import window
from . import xcbq


class Qtile(command.CommandObject):
    """
        This object is the __root__ of the command graph.
    """

    def __init__(self, config,
                 displayName=None, fname=None, no_spawn=False, log=None,
                 state=None):
        logkwargs = {}
        if hasattr(config, "log_level"):
            logkwargs["log_level"] = config.log_level
        if hasattr(config, "log_path"):
            logkwargs["log_path"] = config.log_path
        self.log = log or init_log(**logkwargs)
        logging.getLogger('asyncio').setLevel(logging.CRITICAL)

        self.no_spawn = no_spawn

        self._eventloop = asyncio.get_event_loop()
        self._loop_pending_stop = False
        self._delegated_deletion_list = []

        if not displayName:
            displayName = os.environ.get("DISPLAY")
            if not displayName:
                raise QtileError("No DISPLAY set.")

        if not fname:
            # Dots might appear in the host part of the display name
            # during remote X sessions. Let's strip the host part first.
            displayNum = displayName.partition(":")[2]
            if "." not in displayNum:
                displayName = displayName + ".0"
            fname = command.find_sockfile(displayName)

        try:
            self.conn = xcbq.Connection(displayName)
        except:
            self._eventloop.close()
            raise QtileError("Failed to establish a connection to X server.")
        self.config = config
        self.fname = fname
        hook.init(self)

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
                EventMask.LeaveWindow
            )
        )

        self.root.set_property(
            '_NET_SUPPORTED',
            [self.conn.atoms[x] for x in xcbq.SUPPORTED_ATOMS]
        )

        self.supporting_wm_check_window = self.conn.create_window(-1, -1, 1, 1)
        self.root.set_property(
            '_NET_SUPPORTING_WM_CHECK',
            self.supporting_wm_check_window.wid
        )

        # setup the default cursor
        self.root.set_cursor('left_ptr')

        wmname = getattr(self.config, "wmname", "qtile")
        self.supporting_wm_check_window.set_property('_NET_WM_NAME', wmname)
        self.supporting_wm_check_window.set_property(
            '_NET_SUPPORTING_WM_CHECK',
            self.supporting_wm_check_window.wid
        )

        if config.main:
            config.main(self)

        self.dgroups = None
        if self.config.groups:
            key_binder = None
            if hasattr(self.config, 'dgroups_key_binder'):
                key_binder = self.config.dgroups_key_binder
            self.dgroups = DGroups(self, self.config.groups, key_binder)

        if hasattr(config, "widget_defaults") and config.widget_defaults:
            _Widget.global_defaults = config.widget_defaults
        else:
            _Widget.global_defaults = {}

        for i in self.groups:
            self.groupMap[i.name] = i

        self.currentScreen = None
        self.screens = []
        self._process_screens()
        self.currentScreen = self.screens[0]
        self._drag = None

        self.ignoreEvents = set([
            xcffib.xproto.KeyReleaseEvent,
            xcffib.xproto.ReparentNotifyEvent,
            xcffib.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcffib.xproto.MapNotifyEvent,
            xcffib.xproto.LeaveNotifyEvent,
            xcffib.xproto.FocusOutEvent,
            xcffib.xproto.FocusInEvent,
            xcffib.xproto.NoExposureEvent
        ])

        self.setup_python_dbus()

        self.conn.flush()
        self.conn.xsync()
        self._xpoll()

        self.server = command._Server(self.fname, self, config)

        # Map and Grab keys
        for key in self.config.keys:
            self.mapKey(key)

        # It fixes problems with focus when clicking windows of some specific clients like xterm
        def noop(qtile):
            pass
        self.config.mouse += (Click([], "Button1", command.lazy.function(noop), focus="after"),)

        self.mouseMap = {}
        for i in self.config.mouse:
            if self.mouseMap.get(i.button_code) is None:
                self.mouseMap[i.button_code] = []
            self.mouseMap[i.button_code].append(i)

        self.grabMouse()

        # no_spawn is set when we are restarting; we only want to run the
        # startup hook once.
        if not no_spawn:
            hook.fire("startup_once")
        hook.fire("startup")

        self.scan()
        self.update_net_desktops()
        hook.subscribe.setgroup(self.update_net_desktops)

        if state:
            st = pickle.load(six.BytesIO(state.encode()))
            try:
                st.apply(self)
            except:
                log.exception("failed restoring state")

        self.selection = {
            "PRIMARY": {"owner": None, "selection": ""},
            "CLIPBOARD": {"owner": None, "selection": ""}
        }
        self.setup_selection()

    def setup_selection(self):
        PRIMARY = self.conn.atoms["PRIMARY"]
        CLIPBOARD = self.conn.atoms["CLIPBOARD"]

        self.selection_window = self.conn.create_window(-1, -1, 1, 1)
        self.selection_window.set_attribute(eventmask=EventMask.PropertyChange)
        self.conn.xfixes.select_selection_input(self.selection_window,
                                                "PRIMARY")
        self.conn.xfixes.select_selection_input(self.selection_window,
                                                "CLIPBOARD")

        r = self.conn.conn.core.GetSelectionOwner(PRIMARY).reply()
        self.selection["PRIMARY"]["owner"] = r.owner
        r = self.conn.conn.core.GetSelectionOwner(CLIPBOARD).reply()
        self.selection["CLIPBOARD"]["owner"] = r.owner

        # ask for selection on starup
        self.convert_selection(PRIMARY)
        self.convert_selection(CLIPBOARD)

    def setup_python_dbus(self):
        # This is a little strange. python-dbus internally depends on gobject,
        # so gobject's threads need to be running, and a gobject "main loop
        # thread" needs to be spawned, but we try to let it only interact with
        # us via calls to asyncio's call_soon_threadsafe.
        try:
            # We import dbus here to thrown an ImportError if it isn't
            # available. Since the only reason we're running this thread is
            # because of dbus, if dbus isn't around there's no need to run
            # this thread.
            import dbus  # noqa
            from gi.repository import GLib

            ctxloop = GLib.MainLoop.new(GLib.main_context_default(), False)
            self.delegate_free_at_exit(ctxloop, lambda l: l.quit())
            def gobject_thread():
                self.log.info("GObject thread has started.")
                while not self._loop_pending_stop:
                    try:
                        ctxloop.run()
                    except:
                        if not self._loop_pending_stop:
                            self.log.exception("got exception from gobject")
                self.log.info("GObject thread has exited.")
            self.run_in_executor(gobject_thread)
        except ImportError:
            self.log.warning("importing dbus/gobject failed, dbus will not work.")

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

        # What's going on here is a little funny. What we really want is only
        # screens that don't overlap here; overlapping screens should see the
        # same parts of the root window (i.e. for people doing xrandr
        # --same-as). However, the order that X gives us psuedoscreens in is
        # important, because it indicates what people have chosen via xrandr
        # --primary or whatever. So we need to alias screens that should be
        # aliased, but preserve order as well. See #383.
        xywh = {}
        screenpos = []
        for s in self.conn.pseudoscreens:
            pos = (s.x, s.y)
            (w, h) = xywh.get(pos, (0, 0))
            if pos not in xywh:
                screenpos.append(pos)
            xywh[pos] = (max(w, s.width), max(h, s.height))

        for i, (x, y) in enumerate(screenpos):
            (w, h) = xywh[(x, y)]
            if i + 1 > len(self.config.screens):
                scr = Screen()
            else:
                scr = self.config.screens[i]
            if not self.currentScreen:
                self.currentScreen = scr
            scr._configure(
                self,
                i,
                x,
                y,
                w,
                h,
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
            xcffib.xproto.GrabMode.Async,
            xcffib.xproto.GrabMode.Async,
        )
        if self.numlockMask:
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask,
                True,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.GrabMode.Async,
            )
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask | xcbq.ModMasks["lock"],
                True,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.GrabMode.Async,
            )

    def unmapKey(self, key):
        key_index = (key.keysym, key.modmask & self.validMask)
        if key_index not in self.keyMap:
            return

        code = self.conn.keysym_to_keycode(key.keysym)
        self.root.ungrab_key(code, key.modmask)
        if self.numlockMask:
            self.root.ungrab_key(code, key.modmask | self.numlockMask)
            self.root.ungrab_key(
                code,
                key.modmask | self.numlockMask | xcbq.ModMasks["lock"]
            )
        del(self.keyMap[key_index])

    def update_net_desktops(self):
        try:
            index = self.groups.index(self.currentGroup)
        # TODO: we should really only except ValueError here, AttributeError is
        # an annoying chicken and egg because we're accessing currentScreen
        # (via currentGroup), and when we set up the initial groups, there
        # aren't any screens yet. This can probably be changed when #475 is
        # fixed.
        except (ValueError, AttributeError):
            index = 0

        self.root.set_property("_NET_NUMBER_OF_DESKTOPS", len(self.groups))
        self.root.set_property(
            "_NET_DESKTOP_NAMES", "\0".join([i.name for i in self.groups])
        )
        self.root.set_property("_NET_CURRENT_DESKTOP", index)

    def addGroup(self, name, layout=None, layouts=None):
        if name not in self.groupMap.keys():
            g = _Group(name, layout)
            self.groups.append(g)
            if not layouts:
                layouts = self.config.layouts
            g._configure(layouts, self.config.floating_layout, self)
            self.groupMap[name] = g
            hook.fire("addgroup", self, name)
            hook.fire("changegroup")
            self.update_net_desktops()

            return True
        return False

    def delGroup(self, name):
        # one group per screen is needed
        if len(self.groups) == len(self.screens):
            raise ValueError("Can't delete all groups.")
        if name in self.groupMap.keys():
            group = self.groupMap[name]
            if group.screen and group.screen.previous_group:
                target = group.screen.previous_group
            else:
                target = group.prevGroup()

            # Find a group that's not currently on a screen to bring to the
            # front. This will terminate because of our check above.
            while target.screen:
                target = target.prevGroup()
            for i in list(group.windows):
                i.togroup(target.name)
            if self.currentGroup.name == name:
                self.currentScreen.setGroup(target, save_prev=False)
            self.groups.remove(group)
            del(self.groupMap[name])
            hook.fire("delgroup", self, name)
            hook.fire("changegroup")
            self.update_net_desktops()

    def registerWidget(self, w):
        """
            Register a bar widget. If a widget with the same name already
            exists, this will silently ignore that widget. However, this is
            not necessarily a bug. By default a widget's name is just
            self.__class__.lower(), so putting multiple widgets of the same
            class will alias and one will be inaccessable. Since more than one
            groupbox widget is useful when you have more than one screen, this
            is a not uncommon occurrence. If you want to use the debug
            info for widgets with the same name, set the name yourself.
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
            except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                continue

            if attrs and attrs.map_state == xcffib.xproto.MapState.Unmapped:
                continue
            if state and state[0] == window.WithdrawnState:
                continue
            self.manage(item)

    def unmanage(self, win):
        c = self.windowMap.get(win)
        if c:
            hook.fire("client_killed", c)
            self.reset_gaps(c)
            if getattr(c, "group", None):
                c.group.remove(c)
            del self.windowMap[win]
            self.update_client_list()

    def reset_gaps(self, c):
        if c.strut:
            self.update_gaps((0, 0, 0, 0), c.strut)

    def update_gaps(self, strut, old_strut=None):
        from libqtile.bar import Gap

        (left, right, top, bottom) = strut[:4]
        if old_strut:
            (old_left, old_right, old_top, old_bottom) = old_strut[:4]
            if not left and old_left:
                self.currentScreen.left = None
            elif not right and old_right:
                self.currentScreen.right = None
            elif not top and old_top:
                self.currentScreen.top = None
            elif not bottom and old_bottom:
                self.currentScreen.bottom = None

        if top:
            self.currentScreen.top = Gap(top)
        elif bottom:
            self.currentScreen.bottom = Gap(bottom)
        elif left:
            self.currentScreen.left = Gap(left)
        elif right:
            self.currentScreen.right = Gap(right)
        self.currentScreen.resize()

    def manage(self, w):
        try:
            attrs = w.get_attributes()
            internal = w.get_property("QTILE_INTERNAL")
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return
        if attrs and attrs.override_redirect:
            return

        if w.wid not in self.windowMap:
            if internal:
                try:
                    c = window.Internal(w, self)
                except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                    return
                self.windowMap[w.wid] = c
            else:
                try:
                    c = window.Window(w, self)
                except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                    return

                if w.get_wm_type() == "dock" or c.strut:
                    c.static(self.currentScreen.index)
                else:
                    hook.fire("client_new", c)

                # Window may be defunct because
                # it's been declared static in hook.
                if c.defunct:
                    return
                self.windowMap[w.wid] = c
                # Window may have been bound to a group in the hook.
                if not c.group:
                    self.currentScreen.group.add(c, focus=c.can_steal_focus())
                self.update_client_list()
                hook.fire("client_managed", c)
            return c
        else:
            return self.windowMap[w.wid]

    def update_client_list(self):
        """
        Updates the client stack list
        this is needed for third party tasklists
        and drag and drop of tabs in chrome
        """

        windows = [wid for wid, c in self.windowMap.items() if c.group]
        self.root.set_property("_NET_CLIENT_LIST", windows)
        # TODO: check stack order
        self.root.set_property("_NET_CLIENT_LIST_STACKING", windows)

    def grabMouse(self):
        self.root.ungrab_button(None, None)
        for i in self.config.mouse:
            if isinstance(i, Click) and i.focus:
                # Make a freezing grab on mouse button to gain focus
                # Event will propagate to target window
                grabmode = xcffib.xproto.GrabMode.Sync
            else:
                grabmode = xcffib.xproto.GrabMode.Async
            eventmask = EventMask.ButtonPress
            if isinstance(i, Drag):
                eventmask |= EventMask.ButtonRelease
            self.root.grab_button(
                i.button_code,
                i.modmask,
                True,
                eventmask,
                grabmode,
                xcffib.xproto.GrabMode.Async,
            )
            if self.numlockMask:
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask,
                    True,
                    eventmask,
                    grabmode,
                    xcffib.xproto.GrabMode.Async,
                )
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask | xcbq.ModMasks["lock"],
                    True,
                    eventmask,
                    grabmode,
                    xcffib.xproto.GrabMode.Async,
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

    def delegate_free_at_exit(self, obj, func):
        self._delegated_deletion_list.append((obj, func))

    def do_delegated_free(self, obj):
        if self._loop_pending_stop:
            return
        for i, (o, f) in enumerate(self._delegated_deletion_list):
            if o is obj:
                f(o)
                self._delegated_deletion_list.pop(i)
                break

    def _loop_exception_handler(self, loop, context):
        if not self._loop_pending_stop:
            self.log.exception("Got an exception in poll loop")

    def _stop_event_loop(self):
        self._loop_pending_stop = True
        for (o, f) in self._delegated_deletion_list:
            try:
                f(o)
            except ConnectionException:
                # since we're stopping event loop,
                # print no complains about broken connection.
                pass
            except:
                self.log.warning(
                    "exception occured when deleting delegated object: %s" %
                    type(o))
        self._delegated_deletion_list = []
        self._eventloop.stop()

    def _xpoll(self):
        while True:
            try:
                e = self.conn.conn.poll_for_event()
                if not e:
                    break

                ename = e.__class__.__name__

                if ename.endswith("Event"):
                    ename = ename[:-5]
                if e.__class__ not in self.ignoreEvents:
                    self.log.debug(ename)
                    for h in self.get_target_chain(ename, e):
                        self.log.info("Handling: %s" % ename)
                        r = h(e)
                        if not r:
                            break
            # Catch some bad X exceptions. Since X is event based, race
            # conditions can occur almost anywhere in the code. For
            # example, if a window is created and then immediately
            # destroyed (before the event handler is evoked), when the
            # event handler tries to examine the window properties, it
            # will throw a WindowError exception. We can essentially
            # ignore it, since the window is already dead and we've got
            # another event in the queue notifying us to clean it up.
            except (WindowError, AccessError, DrawableError):
                pass

            except ConnectionException:
                self.log.warning("connection to X server closed")
                self._stop_event_loop()
                break

            except Exception as e:
                error_code = self.conn.conn.has_error()
                if error_code:
                    error_string = xcbq.XCB_CONN_ERRORS[error_code]
                    self.log.exception("Shutting down due to X connection error %s (%s)" %
                        (error_string, error_code))
                    self.conn.disconnect()
                    self._stop_event_loop()

                self.log.exception("Got an exception in poll loop")

        self.conn.flush()

    def loop(self):
        self.server.start()

        self._eventloop.add_signal_handler(
            signal.SIGINT, self._stop_event_loop)
        self._eventloop.add_signal_handler(
            signal.SIGTERM, self._stop_event_loop)
        self._eventloop.set_exception_handler(
            self._loop_exception_handler)

        self.log.info('Adding io watch')
        fd = self.conn.conn.get_file_descriptor()
        self._eventloop.add_reader(fd, self._xpoll)

        try:
            self._eventloop.run_forever()
        finally:
            self.server.close()
            self.log.info('Removing io watch')
            self._eventloop.remove_reader(fd)
            self._eventloop.close()
            try:
                self.conn.disconnect()
            except:
                # since we're closing anyway
                pass

            try:
                # GObject.idle_add is deprecated; changing to GLib
                from gi.repository import GLib
                GLib.idle_add(lambda: None)
            except ImportError:
                pass

    def find_screen(self, x, y):
        """
            Find a screen based on the x and y offset.
        """
        result = []
        for i in self.screens:
            if x >= i.x and x <= i.x + i.width and \
                    y >= i.y and y <= i.y + i.height:
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
        candidate_screens = [
            s for s in candidate_screens
            if x < s.x + s.width and y < s.y + s.width
        ]
        for s in candidate_screens:
            middle_x = s.x + s.width / 2
            middle_y = s.y + s.height / 2
            distance = (x - middle_x) ** 2 + (y - middle_y) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_screen = s
        return closest_screen

    def handle_SelectionNotify(self, e):
        if not getattr(e, "owner", None):
            return

        name = self.conn.atoms.get_name(e.selection)
        self.selection[name]["owner"] = e.owner
        self.selection[name]["selection"] = ""

        self.convert_selection(e.selection)

        hook.fire("selection_notify", name, self.selection[name])

    def convert_selection(self, selection, _type="UTF8_STRING"):
        TYPE = self.conn.atoms[_type]
        self.conn.conn.core.ConvertSelection(self.selection_window.wid,
                                             selection,
                                             TYPE, selection,
                                             xcffib.CurrentTime)

    def handle_PropertyNotify(self, e):
        name = self.conn.atoms.get_name(e.atom)
        # it's the selection property
        if name in ("PRIMARY", "CLIPBOARD"):
            assert e.window == self.selection_window.wid
            prop = self.selection_window.get_property(e.atom, "UTF8_STRING")

            # If the selection property is None, it is unset, which means the
            # clipboard is empty.
            value = prop and prop.value.to_utf8() or six.u("")

            self.selection[name]["selection"] = value
            hook.fire("selection_change", name, self.selection[name])

    def handle_EnterNotify(self, e):
        if e.event in self.windowMap:
            return True
        s = self.find_screen(e.root_x, e.root_y)
        if s:
            self.toScreen(s.index)

    def handle_ClientMessage(self, event):
        atoms = self.conn.atoms

        opcode = event.type
        data = event.data

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
                    (i.selectors, i.name, i.args, i.kwargs)
                )
                if status in (command.ERROR, command.EXCEPTION):
                    self.log.error("KB command error %s: %s" % (i.name, val))
        else:
            return

    def cmd_focus_by_click(self, e):
        wnd = e.child or e.root

        # Additional option for config.py
        # Brings clicked window to front
        if self.config.bring_front_click:
            self.conn.conn.core.ConfigureWindow(
                wnd,
                xcffib.xproto.ConfigWindow.StackMode,
                [xcffib.xproto.StackMode.Above]
            )

        if self.windowMap.get(wnd):
            self.currentGroup.focus(self.windowMap.get(wnd), False)
            self.windowMap.get(wnd).focus(False)

        self.conn.conn.core.AllowEvents(xcffib.xproto.Allow.ReplayPointer, e.time)
        self.conn.conn.flush()

    def handle_ButtonPress(self, e):
        button_code = e.detail
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask

        k = self.mouseMap.get(button_code)
        for m in k:
            if not m or m.modmask & self.validMask != state & self.validMask:
                self.log.info("Ignoring unknown button: %s" % button_code)
                continue
            if isinstance(m, Click):
                for i in m.commands:
                    if i.check(self):
                        if m.focus == "before":
                            self.cmd_focus_by_click(e)
                        status, val = self.server.call(
                            (i.selectors, i.name, i.args, i.kwargs))
                        if m.focus == "after":
                            self.cmd_focus_by_click(e)
                        if status in (command.ERROR, command.EXCEPTION):
                            self.log.error(
                                "Mouse command error %s: %s" % (i.name, val)
                            )
            elif isinstance(m, Drag):
                x = e.event_x
                y = e.event_y
                if m.start:
                    i = m.start
                    if m.focus == "before":
                        self.cmd_focus_by_click(e)
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args, i.kwargs))
                    if status in (command.ERROR, command.EXCEPTION):
                        self.log.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )
                        continue
                else:
                    val = (0, 0)
                if m.focus == "after":
                    self.cmd_focus_by_click(e)
                self._drag = (x, y, val[0], val[1], m.commands)
                self.root.grab_pointer(
                    True,
                    xcbq.ButtonMotionMask |
                    xcbq.AllButtonsMask |
                    xcbq.ButtonReleaseMask,
                    xcffib.xproto.GrabMode.Async,
                    xcffib.xproto.GrabMode.Async,
                )

    def handle_ButtonRelease(self, e):
        button_code = e.detail
        state = e.state & ~xcbq.AllButtonsMask
        if self.numlockMask:
            state = state | self.numlockMask
        k = self.mouseMap.get(button_code)
        for m in k:
            if not m:
                self.log.info(
                    "Ignoring unknown button release: %s" % button_code
                )
                continue
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
                    status, val = self.server.call((
                        i.selectors,
                        i.name,
                        i.args + (rx + dx, ry + dy, e.event_x, e.event_y),
                        i.kwargs
                    ))
                    if status in (command.ERROR, command.EXCEPTION):
                        self.log.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )

    def handle_ConfigureNotify(self, e):
        """
            Handle xrandr events.
        """
        screen = self.currentScreen
        if e.window == self.root.wid and \
                e.width != screen.width and \
                e.height != screen.height:
            screen.resize(0, 0, e.width, e.height)

    def handle_ConfigureRequest(self, e):
        # It's not managed, or not mapped, so we just obey it.
        cw = xcffib.xproto.ConfigWindow
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
        if e.request == xcffib.xproto.Mapping.Keyboard:
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
            c = self.windowMap.get(e.window)
            if c and getattr(c, "group", None):
                try:
                    c.window.unmap()
                    c.state = window.WithdrawnState
                except xcffib.xproto.WindowError:
                    # This means that the window has probably been destroyed,
                    # but we haven't yet seen the DestroyNotify (it is likely
                    # next in the queue). So, we just let these errors pass
                    # since the window is dead.
                    pass
            self.unmanage(e.window)

    def handle_ScreenChangeNotify(self, e):
        hook.fire("screen_change", self, e)

    def toScreen(self, n, warp=True):
        """
        Have Qtile move to screen and put focus there
        """
        if len(self.screens) < n - 1:
            return
        old = self.currentScreen
        self.currentScreen = self.screens[n]
        if old != self.currentScreen:
            hook.fire("current_screen_change")
            self.currentGroup.focus(self.currentWindow, warp)

    def moveToGroup(self, group):
        """
            Create a group if it doesn't exist and move a windows there
        """
        if self.currentWindow and group:
            self.addGroup(group)
            self.currentWindow.togroup(group)

    def _items(self, name):
        if name == "group":
            return True, list(self.groupMap.keys())
        elif name == "layout":
            return True, list(range(len(self.currentGroup.layouts)))
        elif name == "widget":
            return False, list(self.widgetMap.keys())
        elif name == "bar":
            return False, [x.position for x in self.currentScreen.gaps]
        elif name == "window":
            return True, self.listWID()
        elif name == "screen":
            return True, list(range(len(self.screens)))

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

    def call_soon(self, func, *args):
        """ A wrapper for the event loop's call_soon which also flushes the X
        event queue to the server after func is called. """
        if self._loop_pending_stop:
            return
        def f():
            func(*args)
            self.conn.flush()
        self._eventloop.call_soon(f)

    def call_soon_threadsafe(self, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        if self._loop_pending_stop:
            return
        def f():
            func(*args)
            self.conn.flush()
        self._eventloop.call_soon_threadsafe(f)

    def call_later(self, delay, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        if self._loop_pending_stop:
            return
        def f():
            func(*args)
            self.conn.flush()
        self._eventloop.call_later(delay, f)

    def run_in_executor(self, func, *args):
        """ A wrapper for running a function in the event loop's default
        executor. """
        return self._eventloop.run_in_executor(None, func, *args)

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
        return dict((i.name, i.info()) for i in self.groups)

    def cmd_list_widgets(self):
        """
            List of all addressible widget names.
        """
        return list(self.widgetMap.keys())

    def cmd_next_layout(self, group=None):
        """
            Switch to the next layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groupMap.get(group)
        else:
            group = self.currentGroup
        group.nextLayout()

    def cmd_prev_layout(self, group=None):
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
        except KeyError as v:
            return v.args[0]
        self.handle_KeyPress(d)

    def cmd_execute(self, cmd, args):
        """
            Executes the specified command, replacing the current process.
        """
        self._stop_event_loop()
        os.execv(cmd, args)

    def cmd_restart(self):
        """
            Restart qtile using the execute command.
        """
        argv = [sys.executable] + sys.argv
        if '--no-spawn' not in argv:
            argv.append('--no-spawn')

        buf = six.BytesIO()
        pickle.dump(QtileState(self), buf, protocol=0)
        argv = [s for s in argv if not s.startswith('--with-state')]
        argv.append('--with-state=' + buf.getvalue().decode())

        self.cmd_execute(sys.executable, argv)

    def cmd_spawn(self, cmd):
        """
            Run cmd in a shell.

            Example:

                spawn("firefox")
        """
        args = shlex.split(cmd)

        r, w = os.pipe()
        pid = os.fork()
        if pid < 0:
            os.close(r)
            os.close(w)
            return pid

        if pid == 0:
            os.close(r)

            # close qtile's stdin, stdout, stderr so the called process doesn't
            # pollute our xsession-errors.
            os.close(0)
            os.close(1)
            os.close(2)

            pid2 = os.fork()
            if pid2 == 0:
                os.close(w)

                # Open /dev/null as stdin, stdout, stderr
                try:
                    fd = os.open(os.devnull, os.O_RDWR)
                except OSError:
                    # This shouldn't happen, catch it just in case
                    pass
                else:
                    if fd > 0:
                        # Again, this shouldn't happen, but we should just check
                        os.dup2(fd, 0)
                    os.dup2(fd, 1)
                    os.dup2(fd, 2)

                try:
                    os.execvp(args[0], args)
                except OSError:
                    pass
                os._exit(1)
            else:
                # Here it doesn't matter if fork failed or not, we just write
                # its return code and exit.
                os.write(w, str(pid2).encode())
                os.close(w)

                # sys.exit raises SystemExit, which will then be caught by our
                # top level catchall and we'll end up with two qtiles; os._exit
                # actually calls exit.
                os._exit(0)
        else:
            os.close(w)
            os.waitpid(pid, 0)

            # 1024 bytes should be enough for any pid. :)
            pid = os.read(r, 1024)
            os.close(r)
            return int(pid)

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

    def cmd_next_screen(self):
        """
            Move to next screen
        """
        return self.toScreen(
            (self.screens.index(self.currentScreen) + 1) % len(self.screens)
        )

    def cmd_prev_screen(self):
        """
            Move to the previous screen
        """
        return self.toScreen(
            (self.screens.index(self.currentScreen) - 1) % len(self.screens)
        )

    def cmd_windows(self):
        """
            Return info for each client window.
        """
        return [
            i.info() for i in self.windowMap.values()
            if not isinstance(i, window.Internal)
        ]

    def cmd_internal_windows(self):
        """
            Return info for each internal window (bars, for example).
        """
        return [
            i.info() for i in self.windowMap.values()
            if isinstance(i, window.Internal)
        ]

    def cmd_qtile_info(self):
        """
            Returns a dictionary of info on the Qtile instance.
        """
        return dict(socketname=self.fname)

    def cmd_shutdown(self):
        """
            Quit Qtile.
        """
        self._stop_event_loop()

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

        # update window _NET_WM_DESKTOP
        for group in (self.groups[indexa], self.groups[indexb]):
            for w in group.windows:
                w.group = group

    def find_window(self, wid):
        window = self.windowMap.get(wid)
        if window:
            if not window.group.screen:
                self.currentScreen.setGroup(window.group)
            window.group.focus(window, False)

    def cmd_findwindow(self, prompt="window", widget="prompt"):
        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.error("No widget named '%s' present." % widget)
            return

        mb.startInput(
            prompt,
            self.find_window,
            "window",
            strict_completer=True
        )

    def cmd_next_urgent(self):
        try:
            nxt = [w for w in self.windowMap.values() if w.urgent][0]
            nxt.group.cmd_toscreen()
            nxt.group.focus(nxt, False)
        except IndexError:
            pass  # no window had urgent set

    def cmd_togroup(self, prompt="group", widget="prompt"):
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

        mb.startInput(prompt, self.moveToGroup, "group", strict_completer=True)

    def cmd_switchgroup(self, prompt="group", widget="prompt"):
        def f(group):
            if group:
                try:
                    self.groupMap[group].cmd_toscreen()
                except KeyError:
                    self.log.info("No group named '%s' present." % group)
                    pass

        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.warning("No widget named '%s' present." % widget)
            return

        mb.startInput(prompt, f, "group", strict_completer=True)

    def cmd_spawncmd(self, prompt="spawn", widget="prompt",
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
        except KeyError:
            self.log.error("No widget named '%s' present." % widget)

    def cmd_qtilecmd(self, prompt="command",
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
                # c here is used in eval() below
                c = command.CommandRoot(self)  # noqa
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
                if result is not None:
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

    def cmd_add_rule(self, match_args, rule_args, min_priorty=False):
        """
            Add a dgroup rule, returns rule_id needed to remove it
            param: match_args (config.Match arguments)
            param: rule_args (config.Rule arguments)
            param: min_priorty if the rule is added with minimun prioriry(last)
        """
        if not self.dgroups:
            self.log.warning('No dgroups created')
            return

        match = Match(**match_args)
        rule = Rule(match, **rule_args)
        return self.dgroups.add_rule(rule, min_priorty)

    def cmd_remove_rule(self, rule_id):
        self.dgroups.remove_rule(rule_id)

    def cmd_run_external(self, full_path):
        def format_error(path, e):
            s = """Can't call "main" from "{path}"\n\t{err_name}: {err}"""
            return s.format(path=path, err_name=e.__class__.__name__, err=e)

        module_name = os.path.splitext(os.path.basename(full_path))[0]
        dir_path = os.path.dirname(full_path)
        err_str = ""
        local_stdout = six.BytesIO()
        old_stdout = sys.stdout
        sys.stdout = local_stdout
        sys.exc_clear()

        try:
            fp, pathname, description = imp.find_module(module_name, [dir_path])
            module = imp.load_module(module_name, fp, pathname, description)
            module.main(self)
        except ImportError as e:
            fp = None
            err_str += format_error(full_path, e)
        except:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            err_str += traceback.format_exc()
            err_str += format_error(full_path, exc_type(exc_value))
        finally:
            sys.exc_clear()
            sys.stdout = old_stdout
            if fp:
                fp.close()

        return local_stdout.getvalue() + err_str

    def cmd_hide_show_bar(self, position="all"):
        """
            param: position one of: "top", "bottom", "left", "right" or "all"
        """
        if position in ["top", "bottom", "left", "right"]:
            bar = getattr(self.currentScreen, position)
            if bar:
                bar.show(not bar.is_show())
                self.currentGroup.layoutAll()
            else:
                self.log.warning(
                    "Not found bar in position '%s' for hide/show." % position)
        elif position == "all":
            screen = self.currentScreen
            is_show = None
            for bar in [screen.left, screen.right, screen.top, screen.bottom]:
                if bar:
                    if is_show is None:
                        is_show = not bar.is_show()
                    bar.show(is_show)
            if is_show is not None:
                self.currentGroup.layoutAll()
            else:
                self.log.warning("Not found bar for hide/show.")
        else:
            self.log.error("Invalid position value:%s" % position)
