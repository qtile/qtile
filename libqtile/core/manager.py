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

import asyncio
import functools
import io
import logging
import os
import pickle
import shlex
import signal
import sys
import time
import traceback
import warnings
from typing import Optional

import xcffib
import xcffib.xinerama
import xcffib.xproto

from libqtile import command_interface, hook, utils, window
from libqtile.backend.x11 import xcbq
from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import IPCCommandServer, QtileCommandInterface
from libqtile.command_object import (
    CommandError,
    CommandException,
    CommandObject,
)
from libqtile.config import Click, Drag, KeyChord, Match, Rule
from libqtile.config import ScratchPad as ScratchPadConfig
from libqtile.config import Screen
from libqtile.dgroups import DGroups
from libqtile.extension.base import _Extension
from libqtile.group import _Group
from libqtile.lazy import lazy
from libqtile.log_utils import logger
from libqtile.scratchpad import ScratchPad
from libqtile.state import QtileState
from libqtile.utils import get_cache_dir, send_notification
from libqtile.widget.base import _Widget


def _import_module(module_name, dir_path):
    import imp
    fp = None
    try:
        fp, pathname, description = imp.find_module(module_name, [dir_path])
        module = imp.load_module(module_name, fp, pathname, description)
    finally:
        if fp:
            fp.close()
    return module


def handle_exception(loop, context):
    if "exception" in context:
        logger.error(context["exception"], exc_info=True)
    else:
        logger.error("exception in event loop: %s", context)


class Qtile(CommandObject):
    """This object is the `root` of the command graph"""
    def __init__(
        self,
        kore,
        config,
        eventloop,
        no_spawn=False,
        state=None
    ):
        self._restart = False
        self.no_spawn = no_spawn

        self.mouse_position = (0, 0)

        self.core = kore
        self.config = config
        hook.init(self)

        self.windows_map = {}
        self.widgets_map = {}
        self.groups_map = {}
        self.groups = []
        self.keys_map = {}
        self.current_chord = False

        self.numlock_mask, self.valid_mask = self.core.masks

        self.core.wmname = getattr(self.config, "wmname", "qtile")
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

        if hasattr(config, "extension_defaults") and config.extension_defaults:
            _Extension.global_defaults = config.extension_defaults
        else:
            _Extension.global_defaults = {}

        for installed_extension in _Extension.installed_extensions:
            installed_extension._configure(self)

        for i in self.groups:
            self.groups_map[i.name] = i

        for grp in self.config.groups:
            if isinstance(grp, ScratchPadConfig):
                sp = ScratchPad(grp.name, grp.dropdowns, grp.label)
                sp._configure([self.config.floating_layout],
                              self.config.floating_layout, self)
                self.groups.append(sp)
                self.groups_map[sp.name] = sp

        self._eventloop = eventloop
        self.setup_eventloop()
        self.server = IPCCommandServer(self)

        self.current_screen = None
        self.screens = []
        self._process_screens()
        self.current_screen = self.screens[0]
        self._drag = None

        self.conn.flush()
        self.conn.xsync()
        self.core._xpoll()

        # Map and Grab keys
        for key in self.config.keys:
            self.grab_key(key)

        # It fixes problems with focus when clicking windows of some specific clients like xterm
        def noop(qtile):
            pass
        self.config.mouse += (Click([], "Button1", lazy.function(noop), focus="after"),)

        self.mouse_map = {}
        for i in self.config.mouse:
            if self.mouse_map.get(i.button_code) is None:
                self.mouse_map[i.button_code] = []
            self.mouse_map[i.button_code].append(i)

        self.grab_mouse()

        # no_spawn is set when we are restarting; we only want to run the
        # startup hook once.
        if not no_spawn:
            hook.fire("startup_once")
        hook.fire("startup")

        if state:
            st = pickle.load(io.BytesIO(state.encode()))
            try:
                st.apply(self)
            except:  # noqa: E722
                logger.exception("failed restoring state")

        self.core.scan()
        self.update_net_desktops()
        hook.subscribe.setgroup(self.update_net_desktops)

        hook.fire("startup_complete")

    @property
    def root(self):
        return self.core._root

    @property
    def conn(self):
        return self.core.conn

    @property
    def selection(self):
        return self.core._selection

    def setup_eventloop(self) -> None:
        self._eventloop.add_signal_handler(signal.SIGINT, self.stop)
        self._eventloop.add_signal_handler(signal.SIGTERM, self.stop)
        self._eventloop.set_exception_handler(handle_exception)

        logger.debug('Adding io watch')
        self.core.setup_listener(self, self._eventloop)

        self._stopped_event = asyncio.Event()

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
            from gi.repository import GLib  # type: ignore

            def gobject_thread():
                ctx = GLib.main_context_default()
                while not self._stopped_event.is_set():
                    try:
                        ctx.iteration(True)
                    except Exception:
                        logger.exception("got exception from gobject")
            self._glib_loop = self.run_in_executor(gobject_thread)
        except ImportError:
            logger.warning("importing dbus/gobject failed, dbus will not work.")
            self._glib_loop = None

    async def async_loop(self) -> None:
        """Run the event loop

        Finalizes the Qtile instance on exit.
        """
        try:
            await self._stopped_event.wait()
        finally:
            await self.finalize()

        self._eventloop.stop()

    def maybe_restart(self) -> None:
        """If set, restart the qtile instance"""
        if self._restart:
            logger.warning('Restarting Qtile with os.execv(...)')
            os.execv(*self._restart)

    def stop(self):
        # stop gets called in a variety of ways, including from restart().
        # let's only do a real shutdown if we're not about to re-exec.
        if not self._restart:
            self.graceful_shutdown()

        logger.debug('Stopping qtile')
        self._stopped_event.set()

    def restart(self):
        argv = [sys.executable] + sys.argv
        if '--no-spawn' not in argv:
            argv.append('--no-spawn')
        buf = io.BytesIO()
        try:
            pickle.dump(QtileState(self), buf, protocol=0)
        except:  # noqa: E722
            logger.error("Unable to pickle qtile state")
        argv = [s for s in argv if not s.startswith('--with-state')]
        argv.append('--with-state=' + buf.getvalue().decode())
        self._restart = (sys.executable, argv)
        self.stop()

    async def finalize(self):
        self._eventloop.remove_signal_handler(signal.SIGINT)
        self._eventloop.remove_signal_handler(signal.SIGTERM)
        self._eventloop.set_exception_handler(None)

        if self._glib_loop:
            try:
                from gi.repository import GLib
                GLib.idle_add(lambda: None)
                await self._glib_loop
            except ImportError:
                pass

        try:
            for widget in self.widgets_map.values():
                widget.finalize()

            for layout in self.config.layouts:
                layout.finalize()

            for screen in self.screens:
                for bar in [screen.top, screen.bottom, screen.left, screen.right]:
                    if bar is not None:
                        bar.finalize()
        except:  # noqa: E722
            logger.exception('exception during finalize')
            self.core.remove_listener()

    def _process_fake_screens(self):
        """
        Since Xephyr and Xnest don't really support offset screens, we'll fake
        it here for testing, (or if you want to partition a physical monitor
        into separate screens)
        """
        for i, s in enumerate(self.config.fake_screens):
            # should have x,y, width and height set
            s._configure(self, i, s.x, s.y, s.width, s.height, self.groups[i])
            if not self.current_screen:
                self.current_screen = s
            self.screens.append(s)

    def _process_screens(self) -> None:
        if hasattr(self.config, 'fake_screens'):
            self._process_fake_screens()
            return

        screen_info = self.core.get_screen_info()

        for i, (x, y, w, h) in enumerate(screen_info):
            if i + 1 > len(self.config.screens):
                scr = Screen()
            else:
                scr = self.config.screens[i]

            if not self.current_screen:
                self.current_screen = scr

            scr._configure(
                self, i, x, y, w, h, self.groups[i],
            )
            self.screens.append(scr)

    def paint_screen(self, screen, image_path, mode=None):
        self.core.painter.paint(screen, image_path, mode)

    def process_configure(self, width: int, height: int) -> None:
        screen = self.current_screen
        screen.resize(0, 0, width, height)

    def process_key_event(self, keysym: int, mask: int) -> None:
        key = self.keys_map.get((keysym, mask), None)
        if key is None:
            logger.info("Ignoring unknown keysym: {keysym}, mask: {mask}".format(keysym=keysym, mask=mask))
            return

        if isinstance(key, KeyChord):
            self.grab_chord(key)
        else:
            for cmd in key.commands:
                if cmd.check(self):
                    status, val = self.server.call(
                        (cmd.selectors, cmd.name, cmd.args, cmd.kwargs)
                    )
                    if status in (command_interface.ERROR, command_interface.EXCEPTION):
                        logger.error("KB command error %s: %s" % (cmd.name, val))
            else:
                if self.current_chord is True or (self.current_chord and key.key == "Escape"):
                    self.ungrab_chord()
                return

    def grab_keys(self) -> None:
        self.core.ungrab_keys()
        for key in self.keys_map.values():
            self.grab_key(key)

    def grab_key(self, key) -> None:
        keysym, modmask, mask_key = self.core.lookup_key(key)
        self.core.grab_key(keysym, modmask)
        self.keys_map[(keysym, mask_key)] = key

    def ungrab_key(self, key) -> None:
        keysym, modmask, mask_key = self.core.lookup_key(key)
        key = self.keys_map.pop((keysym, mask_key))
        if key is not None:
            self.core.ungrab_key(keysym, modmask)

    def clear_chords(self) -> None:
        self.core.ungrab_keys()
        self.keys_map.clear()

    def grab_chord(self, chord) -> None:
        self.current_chord = chord.mode if chord.mode != "" else True
        if self.current_chord:
            hook.fire("enter_chord", self.current_chord)
        self.clear_chords()
        for key in chord.submapings:
            self.grab_key(key)

    def ungrab_chord(self) -> None:
        self.current_chord = False
        hook.fire("leave_chord")
        self.clear_chords()
        for key in self.config.keys:
            self.grab_key(key)

    def grab_mouse(self) -> None:
        self.core.ungrab_buttons()
        for mouse in self.config.mouse:
            self.core.grab_button(mouse)

    def update_net_desktops(self) -> None:
        try:
            index = self.groups.index(self.current_group)
        # TODO: we should really only except ValueError here, AttributeError is
        # an annoying chicken and egg because we're accessing current_screen
        # (via current_group), and when we set up the initial groups, there
        # aren't any screens yet. This can probably be changed when #475 is
        # fixed.
        except (ValueError, AttributeError):
            index = 0

        self.core.update_net_desktops(self.groups, index)

    def update_client_list(self) -> None:
        """Updates the client stack list

        This is needed for third party tasklists and drag and drop of tabs in
        chrome
        """
        windows = [wid for wid, c in self.windows_map.items() if c.group]
        self.core.update_client_list(windows)

    def add_group(self, name, layout=None, layouts=None, label=None):
        if name not in self.groups_map.keys():
            g = _Group(name, layout, label=label)
            self.groups.append(g)
            if not layouts:
                layouts = self.config.layouts
            g._configure(layouts, self.config.floating_layout, self)
            self.groups_map[name] = g
            hook.fire("addgroup", self, name)
            hook.fire("changegroup")
            self.update_net_desktops()

            return True
        return False

    def delete_group(self, name):
        # one group per screen is needed
        if len(self.groups) == len(self.screens):
            raise ValueError("Can't delete all groups.")
        if name in self.groups_map.keys():
            group = self.groups_map[name]
            if group.screen and group.screen.previous_group:
                target = group.screen.previous_group
            else:
                target = group.get_previous_group()

            # Find a group that's not currently on a screen to bring to the
            # front. This will terminate because of our check above.
            while target.screen:
                target = target.get_previous_group()
            for i in list(group.windows):
                i.togroup(target.name)
            if self.current_group.name == name:
                self.current_screen.set_group(target, save_prev=False)
            self.groups.remove(group)
            del(self.groups_map[name])
            hook.fire("delgroup", self, name)
            hook.fire("changegroup")
            self.update_net_desktops()

    def register_widget(self, w):
        """Register a bar widget

        If a widget with the same name already exists, this will silently
        ignore that widget. However, this is not necessarily a bug. By default
        a widget's name is just ``self.__class__.lower()``, so putting multiple
        widgets of the same class will alias and one will be inaccessible.
        Since more than one groupbox widget is useful when you have more than
        one screen, this is a not uncommon occurrence. If you want to use the
        debug info for widgets with the same name, set the name yourself.
        """
        if w.name:
            if w.name in self.widgets_map:
                return
            self.widgets_map[w.name] = w

    @functools.lru_cache()
    def color_pixel(self, name):
        return self.conn.screens[0].default_colormap.alloc_color(name).pixel

    @property
    def current_layout(self):
        return self.current_group.layout

    @property
    def current_group(self):
        return self.current_screen.group

    @property
    def current_window(self):
        return self.current_screen.group.current_window

    def reset_gaps(self, c):
        if c.strut:
            self.update_gaps((0, 0, 0, 0), c.strut)

    def update_gaps(self, strut, old_strut=None):
        from libqtile.bar import Gap

        (left, right, top, bottom) = strut[:4]
        if old_strut:
            (old_left, old_right, old_top, old_bottom) = old_strut[:4]
            if not left and old_left:
                self.current_screen.left = None
            elif not right and old_right:
                self.current_screen.right = None
            elif not top and old_top:
                self.current_screen.top = None
            elif not bottom and old_bottom:
                self.current_screen.bottom = None

        if top:
            self.current_screen.top = Gap(top)
        elif bottom:
            self.current_screen.bottom = Gap(bottom)
        elif left:
            self.current_screen.left = Gap(left)
        elif right:
            self.current_screen.right = Gap(right)
        self.current_screen.resize()

    def map_window(self, window: xcbq.Window) -> None:
        c = self.manage(window)
        if c and (not c.group or not c.group.screen):
            return
        window.map()

    def unmap_window(self, window_id) -> None:
        c = self.windows_map.get(window_id)
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
        self.unmanage(window_id)

    def manage(self, w):
        try:
            attrs = w.get_attributes()
            internal = w.get_property("QTILE_INTERNAL")
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return
        if attrs and attrs.override_redirect:
            return

        if w.wid not in self.windows_map:
            if internal:
                try:
                    c = window.Internal(w, self)
                except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                    return
                self.windows_map[w.wid] = c
            else:
                try:
                    c = window.Window(w, self)
                except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                    return

                if w.get_wm_type() == "dock" or c.strut:
                    c.static(self.current_screen.index)
                else:
                    hook.fire("client_new", c)

                # Window may be defunct because
                # it's been declared static in hook.
                if c.defunct:
                    return
                self.windows_map[w.wid] = c
                # Window may have been bound to a group in the hook.
                if not c.group:
                    self.current_screen.group.add(c, focus=c.can_steal_focus())
                self.update_client_list()
                hook.fire("client_managed", c)
            return c
        else:
            return self.windows_map[w.wid]

    def unmanage(self, win):
        c = self.windows_map.get(win)
        if c:
            hook.fire("client_killed", c)
            self.reset_gaps(c)
            if getattr(c, "group", None):
                c.group.remove(c)
            del self.windows_map[win]
            self.update_client_list()
        if self.current_window is None:
            self.conn.fixup_focus()

    def graceful_shutdown(self):
        """
        Try and gracefully shutdown windows before exiting with SIGTERM, vs.
        just closing the X session and having the X server send them all
        SIGKILL.
        """

        def get_interesting_pid(win):
            # We don't need to kill Internal or Static windows, they're qtile
            # managed and don't have any state.
            if not isinstance(win, window.Window):
                return None
            try:
                return win.window.get_net_wm_pid()
            except Exception:
                logger.exception("Got an exception in getting the window pid")
                return None
        pids = map(get_interesting_pid, self.windows_map.values())
        pids = list(filter(lambda x: x is not None, pids))

        # Give the windows a chance to shut down nicely.
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                # might have died recently
                pass

        def still_alive(pid):
            # most pids will not be children, so we can't use wait()
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

        # give everyone a little time to exit and write their state. but don't
        # sleep forever (1s).
        for i in range(10):
            pids = list(filter(still_alive, pids))
            if len(pids) == 0:
                break
            time.sleep(0.1)

    def find_screen(self, x, y):
        """Find a screen based on the x and y offset"""
        result = []
        for i in self.screens:
            if i.x <= x <= i.x + i.width and \
                    i.y <= y <= i.y + i.height:
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
            if i.x <= x <= i.x + i.width:
                x_match.append(i)
            if i.y <= y <= i.y + i.height:
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
            if x < s.x + s.width and y < s.y + s.height
        ]
        for s in candidate_screens:
            middle_x = s.x + s.width / 2
            middle_y = s.y + s.height / 2
            distance = (x - middle_x) ** 2 + (y - middle_y) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_screen = s
        return closest_screen

    def enter_event(self, event) -> Optional[bool]:
        if event.event in self.windows_map:
            return True
        screen = self.find_screen(event.root_x, event.root_y)
        if screen:
            self.focus_screen(screen.index, warp=False)
        return None

    def cmd_focus_by_click(self, e):
        """Bring a window to the front

        Parameters
        ==========
        e : xcb event
            Click event used to determine window to focus
        """
        wnd = e.child or e.root

        # Additional option for config.py
        # Brings clicked window to front
        if self.config.bring_front_click:
            self.conn.conn.core.ConfigureWindow(
                wnd,
                xcffib.xproto.ConfigWindow.StackMode,
                [xcffib.xproto.StackMode.Above]
            )

        window = self.windows_map.get(wnd)
        if window and not window.window.get_property('QTILE_INTERNAL'):
            self.current_group.focus(self.windows_map.get(wnd), False)
            self.windows_map.get(wnd).focus(False)

        self.conn.conn.core.AllowEvents(xcffib.xproto.Allow.ReplayPointer, e.time)
        self.conn.conn.flush()

    def process_button_click(self, button_code, state, x, y, event) -> None:
        self.mouse_position = (x, y)
        k = self.mouse_map.get(button_code)
        for m in k:
            try:
                modmask = xcbq.translate_masks(m.modifiers)
            except xcbq.XCBQError as e:
                raise utils.QtileError(e)
            if not m or modmask & self.valid_mask != state & self.valid_mask:
                logger.info("Ignoring unknown button: %s" % button_code)
                continue
            if isinstance(m, Click):
                for i in m.commands:
                    if i.check(self):
                        if m.focus == "before":
                            self.cmd_focus_by_click(event)
                        status, val = self.server.call(
                            (i.selectors, i.name, i.args, i.kwargs))
                        if m.focus == "after":
                            self.cmd_focus_by_click(event)
                        if status in (command_interface.ERROR, command_interface.EXCEPTION):
                            logger.error(
                                "Mouse command error %s: %s" % (i.name, val)
                            )
            elif isinstance(m, Drag):
                if m.start:
                    i = m.start
                    if m.focus == "before":
                        self.cmd_focus_by_click(event)
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args, i.kwargs))
                    if status in (command_interface.ERROR, command_interface.EXCEPTION):
                        logger.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )
                        continue
                else:
                    val = (0, 0)
                if m.focus == "after":
                    self.cmd_focus_by_click(event)
                self._drag = (x, y, val[0], val[1], m.commands)
                self.core.grab_pointer()

    def process_button_release(self, button_code):
        k = self.mouse_map.get(button_code)
        for m in k:
            if not m:
                logger.info(
                    "Ignoring unknown button release: %s" % button_code
                )
                continue
            if isinstance(m, Drag):
                self._drag = None
                self.core.ungrab_pointer()

    def process_button_motion(self, x, y):
        self.mouse_position = (x, y)

        if self._drag is None:
            return
        ox, oy, rx, ry, cmd = self._drag
        dx = x - ox
        dy = y - oy
        if dx or dy:
            for i in cmd:
                if i.check(self):
                    status, val = self.server.call((
                        i.selectors,
                        i.name,
                        i.args + (rx + dx, ry + dy),
                        i.kwargs
                    ))
                    if status in (command_interface.ERROR, command_interface.EXCEPTION):
                        logger.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )

    def focus_screen(self, n, warp=True):
        """Have Qtile move to screen and put focus there"""
        if n >= len(self.screens):
            return
        old = self.current_screen
        self.current_screen = self.screens[n]
        if old != self.current_screen:
            hook.fire("current_screen_change")
            hook.fire("setgroup")
            old.group.layout_all()
            self.current_group.focus(self.current_window, warp)

    def move_to_group(self, group):
        """Create a group if it doesn't exist and move
        the current window there"""
        if self.current_window and group:
            self.add_group(group)
            self.current_window.togroup(group)

    def _items(self, name):
        if name == "group":
            return True, list(self.groups_map.keys())
        elif name == "layout":
            return True, list(range(len(self.current_group.layouts)))
        elif name == "widget":
            return False, list(self.widgets_map.keys())
        elif name == "bar":
            return False, [x.position for x in self.current_screen.gaps]
        elif name == "window":
            return True, self.list_wids()
        elif name == "screen":
            return True, list(range(len(self.screens)))

    def _select(self, name, sel):
        if name == "group":
            if sel is None:
                return self.current_group
            else:
                return self.groups_map.get(sel)
        elif name == "layout":
            if sel is None:
                return self.current_group.layout
            else:
                return utils.lget(self.current_group.layouts, sel)
        elif name == "widget":
            return self.widgets_map.get(sel)
        elif name == "bar":
            return getattr(self.current_screen, sel)
        elif name == "window":
            if sel is None:
                return self.current_window
            else:
                return self.client_from_wid(sel)
        elif name == "screen":
            if sel is None:
                return self.current_screen
            else:
                return utils.lget(self.screens, sel)

    def list_wids(self):
        return [i.window.wid for i in self.windows_map.values()]

    def client_from_wid(self, wid):
        for i in self.windows_map.values():
            if i.window.wid == wid:
                return i
        return None

    def call_soon(self, func, *args):
        """ A wrapper for the event loop's call_soon which also flushes the X
        event queue to the server after func is called. """
        def f():
            func(*args)
            self.conn.flush()
        return self._eventloop.call_soon(f)

    def call_soon_threadsafe(self, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        def f():
            func(*args)
            self.conn.flush()
        return self._eventloop.call_soon_threadsafe(f)

    def call_later(self, delay, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        def f():
            func(*args)
            self.conn.flush()
        return self._eventloop.call_later(delay, f)

    def run_in_executor(self, func, *args):
        """ A wrapper for running a function in the event loop's default
        executor. """
        return self._eventloop.run_in_executor(None, func, *args)

    def cmd_debug(self):
        """Set log level to DEBUG"""
        logger.setLevel(logging.DEBUG)
        logger.debug('Switching to DEBUG threshold')

    def cmd_info(self):
        """Set log level to INFO"""
        logger.setLevel(logging.INFO)
        logger.info('Switching to INFO threshold')

    def cmd_warning(self):
        """Set log level to WARNING"""
        logger.setLevel(logging.WARNING)
        logger.warning('Switching to WARNING threshold')

    def cmd_error(self):
        """Set log level to ERROR"""
        logger.setLevel(logging.ERROR)
        logger.error('Switching to ERROR threshold')

    def cmd_critical(self):
        """Set log level to CRITICAL"""
        logger.setLevel(logging.CRITICAL)
        logger.critical('Switching to CRITICAL threshold')

    def cmd_loglevel(self):
        return logger.level

    def cmd_loglevelname(self):
        return logging.getLevelName(logger.level)

    def cmd_pause(self):
        """Drops into pdb"""
        import pdb
        pdb.set_trace()

    def cmd_groups(self):
        """Return a dictionary containing information for all groups

        Examples
        ========

            groups()
        """
        return {i.name: i.info() for i in self.groups}

    def cmd_get_info(self):
        """Prints info for all groups"""
        warnings.warn("The `get_info` command is deprecated, use `groups`", DeprecationWarning)
        return self.cmd_groups()

    def get_mouse_position(self):
        return self.mouse_position

    def cmd_display_kb(self, *args):
        """Display table of key bindings"""
        class FormatTable:
            def __init__(self):
                self.max_col_size = []
                self.rows = []

            def add(self, row):
                n = len(row) - len(self.max_col_size)
                if n > 0:
                    self.max_col_size += [0] * n
                for i, f in enumerate(row):
                    if len(f) > self.max_col_size[i]:
                        self.max_col_size[i] = len(f)
                self.rows.append(row)

            def getformat(self):
                format_string = " ".join("%-{0:d}s".format(max_col_size + 2) for max_col_size in self.max_col_size)
                return format_string + "\n", len(self.max_col_size)

            def expandlist(self, list, n):
                if not list:
                    return ["-" * max_col_size for max_col_size in self.max_col_size]
                n -= len(list)
                if n > 0:
                    list += [""] * n
                return list

            def __str__(self):
                format, n = self.getformat()
                return "".join([format % tuple(self.expandlist(row, n)) for row in self.rows])

        result = FormatTable()
        result.add(["KeySym", "Mod", "Command", "Desc"])
        result.add([])
        rows = []
        for (ks, kmm), k in self.keys_map.items():
            if not k.commands:
                continue
            name = ", ".join(xcbq.rkeysyms.get(ks, ("<unknown>", )))
            modifiers = ", ".join(xcbq.translate_modifiers(kmm))
            allargs = ", ".join(
                [repr(value) for value in k.commands[0].args] +
                ["%s = %s" % (keyword, repr(value)) for keyword, value in k.commands[0].kwargs.items()]
            )
            rows.append((name, str(modifiers), "{0:s}({1:s})".format(k.commands[0].name, allargs), k.desc))
        rows.sort()
        for row in rows:
            result.add(row)
        return str(result)

    def cmd_list_widgets(self):
        """List of all addressible widget names"""
        return list(self.widgets_map.keys())

    def cmd_to_layout_index(self, index, group=None):
        """Switch to the layout with the given index in self.layouts.

        Parameters
        ==========
        index :
            Index of the layout in the list of layouts.
        group :
            Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groups_map.get(group)
        else:
            group = self.current_group
        group.use_layout(index)

    def cmd_next_layout(self, group=None):
        """Switch to the next layout.

        Parameters
        ==========
        group :
            Group name. If not specified, the current group is assumed
        """
        if group:
            group = self.groups_map.get(group)
        else:
            group = self.current_group
        group.use_next_layout()

    def cmd_prev_layout(self, group=None):
        """Switch to the previous layout.

        Parameters
        ==========
        group :
            Group name. If not specified, the current group is assumed
        """
        if group:
            group = self.groups_map.get(group)
        else:
            group = self.current_group
        group.use_previous_layout()

    def cmd_screens(self):
        """Return a list of dictionaries providing information on all screens"""
        lst = [dict(
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
        ) for i in self.screens]
        return lst

    def cmd_simulate_keypress(self, modifiers, key):
        """Simulates a keypress on the focused window.

        Parameters
        ==========
        modifiers :
            A list of modifier specification strings. Modifiers can be one of
            "shift", "lock", "control" and "mod1" - "mod5".
        key :
            Key specification.

        Examples
        ========
            simulate_keypress(["control", "mod2"], "k")
        """
        # FIXME: This needs to be done with sendevent, once we have that fixed.
        try:
            modmasks = xcbq.translate_masks(modifiers)
            keysym = xcbq.keysyms.get(key)
        except xcbq.XCBQError as e:
            raise CommandError(str(e))

        class DummyEv:
            pass

        d = DummyEv()
        d.detail = self.conn.first_sym_to_code[keysym]
        d.state = modmasks
        self.core.handle_KeyPress(d)

    def cmd_validate_config(self):
        try:
            self.config.load()
        except Exception as error:
            send_notification("Configuration check", str(error.__context__))
        else:
            send_notification("Configuration check", "No error found!")

    def cmd_restart(self):
        """Restart qtile"""
        try:
            self.config.load()
        except Exception as error:
            logger.error("Preventing restart because of a configuration error: {}".format(error))
            send_notification("Configuration error", str(error.__context__))
            return
        self.restart()

    def cmd_spawn(self, cmd):
        """Run cmd in a shell.

        cmd may be a string, which is parsed by shlex.split, or a list (similar
        to subprocess.Popen).

        Examples
        ========

            spawn("firefox")

            spawn(["xterm", "-T", "Temporary terminal"])
        """
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = list(cmd)

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
                try:
                    # if qtile was installed in a virutal env, we don't
                    # necessarily want to propagate that to children
                    # applications, since it may change e.g. the behavior
                    # of shells that spawn python applications
                    del os.environ['VIRTUAL_ENV']
                except KeyError:
                    pass

                # Open /dev/null as stdin, stdout, stderr
                try:
                    fd = os.open(os.devnull, os.O_RDWR)
                except OSError:
                    # This shouldn't happen, catch it just in case
                    pass
                else:
                    # For Python >=3.4, need to set file descriptor to inheritable
                    try:
                        os.set_inheritable(fd, True)
                    except AttributeError:
                        pass

                    # Again, this shouldn't happen, but we should just check
                    if fd > 0:
                        os.dup2(fd, 0)

                    os.dup2(fd, 1)
                    os.dup2(fd, 2)

                try:
                    os.execvp(args[0], args)
                except OSError as e:
                    logger.error("failed spawn: \"{0}\"\n{1}".format(cmd, e))

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
        """Return "OK" if Qtile is running"""
        return "OK"

    def cmd_sync(self):
        """Sync the X display. Should only be used for development"""
        self.conn.flush()

    def cmd_to_screen(self, n):
        """Warp focus to screen n, where n is a 0-based screen number

        Examples
        ========

            to_screen(0)
        """
        return self.focus_screen(n)

    def cmd_next_screen(self):
        """Move to next screen"""
        return self.focus_screen(
            (self.screens.index(self.current_screen) + 1) % len(self.screens)
        )

    def cmd_prev_screen(self):
        """Move to the previous screen"""
        return self.focus_screen(
            (self.screens.index(self.current_screen) - 1) % len(self.screens)
        )

    def cmd_windows(self):
        """Return info for each client window"""
        return [
            i.info() for i in self.windows_map.values()
            if not isinstance(i, window.Internal)
        ]

    def cmd_internal_windows(self):
        """Return info for each internal window (bars, for example)"""
        return [
            i.info() for i in self.windows_map.values()
            if isinstance(i, window.Internal)
        ]

    def cmd_qtile_info(self):
        """Returns a dictionary of info on the Qtile instance"""
        return {}

    def cmd_shutdown(self):
        """Quit Qtile"""
        self.stop()

    def cmd_switch_groups(self, groupa, groupb):
        """Switch position of groupa to groupb"""
        if groupa not in self.groups_map or groupb not in self.groups_map:
            return

        indexa = self.groups.index(self.groups_map[groupa])
        indexb = self.groups.index(self.groups_map[groupb])

        self.groups[indexa], self.groups[indexb] = \
            self.groups[indexb], self.groups[indexa]
        hook.fire("setgroup")

        # update window _NET_WM_DESKTOP
        for group in (self.groups[indexa], self.groups[indexb]):
            for w in group.windows:
                w.group = group

    def find_window(self, wid):
        window = self.windows_map.get(wid)
        if window:
            if not window.group.screen:
                self.current_screen.set_group(window.group)
            window.group.focus(window, False)

    def cmd_findwindow(self, prompt="window", widget="prompt"):
        """Launch prompt widget to find a window of the given name

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "window")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        mb = self.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(
            prompt,
            self.find_window,
            "window",
            strict_completer=True
        )

    def cmd_next_urgent(self):
        """Focus next window with urgent hint"""
        try:
            nxt = [w for w in self.windows_map.values() if w.urgent][0]
            nxt.group.cmd_toscreen()
            nxt.group.focus(nxt)
        except IndexError:
            pass  # no window had urgent set

    def cmd_togroup(self, prompt="group", widget="prompt"):
        """Launch prompt widget to move current window to a given group

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "group")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        if not self.current_window:
            logger.warning("No window to move")
            return

        mb = self.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(prompt, self.move_to_group, "group", strict_completer=True)

    def cmd_switchgroup(self, prompt="group", widget="prompt"):
        """Launch prompt widget to switch to a given group to the current screen

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "group")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        def f(group):
            if group:
                try:
                    self.groups_map[group].cmd_toscreen()
                except KeyError:
                    logger.info("No group named '{0:s}' present.".format(group))

        mb = self.widgets_map.get(widget)
        if not mb:
            logger.warning("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(prompt, f, "group", strict_completer=True)

    def cmd_spawncmd(self, prompt="spawn", widget="prompt",
                     command="%s", complete="cmd"):
        """Spawn a command using a prompt widget, with tab-completion.

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "spawn: ").
        widget :
            Name of the prompt widget (default: "prompt").
        command :
            command template (default: "%s").
        complete :
            Tab completion function (default: "cmd")
        """
        def f(args):
            if args:
                self.cmd_spawn(command % args)
        try:
            mb = self.widgets_map[widget]
            mb.start_input(prompt, f, complete)
        except KeyError:
            logger.error("No widget named '{0:s}' present.".format(widget))

    def cmd_qtilecmd(self, prompt="command",
                     widget="prompt", messenger="xmessage") -> None:
        """Execute a Qtile command using the client syntax

        Tab completion aids navigation of the command tree

        Parameters
        ==========
        prompt :
            Text to display at the prompt (default: "command: ")
        widget :
            Name of the prompt widget (default: "prompt")
        messenger :
            Command to display output, set this to None to disable (default:
            "xmessage")
        """
        def f(cmd):
            if cmd:
                # c here is used in eval() below
                q = QtileCommandInterface(self)
                c = InteractiveCommandClient(q)  # noqa: F841
                try:
                    cmd_arg = str(cmd).split(' ')
                except AttributeError:
                    return
                cmd_len = len(cmd_arg)
                if cmd_len == 0:
                    logger.info('No command entered.')
                    return
                try:
                    result = eval(u'c.{0:s}'.format(cmd))
                except (CommandError, CommandException, AttributeError) as err:
                    logger.error(err)
                    result = None
                if result is not None:
                    from pprint import pformat
                    message = pformat(result)
                    if messenger:
                        self.cmd_spawn('{0:s} "{1:s}"'.format(messenger, message))
                    logger.debug(result)

        mb = self.widgets_map[widget]
        if not mb:
            logger.error("No widget named {0:s} present.".format(widget))
            return
        mb.start_input(prompt, f, "qshell")

    def cmd_addgroup(self, group, label=None, layout=None, layouts=None):
        """Add a group with the given name"""
        return self.add_group(name=group, layout=layout, layouts=layouts, label=label)

    def cmd_delgroup(self, group):
        """Delete a group with the given name"""
        return self.delete_group(group)

    def cmd_add_rule(self, match_args, rule_args, min_priorty=False):
        """Add a dgroup rule, returns rule_id needed to remove it

        Parameters
        ==========
        match_args :
            config.Match arguments
        rule_args :
            config.Rule arguments
        min_priorty :
            If the rule is added with minimum prioriry (last) (default: False)
        """
        if not self.dgroups:
            logger.warning('No dgroups created')
            return

        match = Match(**match_args)
        rule = Rule(match, **rule_args)
        return self.dgroups.add_rule(rule, min_priorty)

    def cmd_remove_rule(self, rule_id):
        """Remove a dgroup rule by rule_id"""
        self.dgroups.remove_rule(rule_id)

    def cmd_run_external(self, full_path):
        """Run external Python script"""
        def format_error(path, e):
            s = """Can't call "main" from "{path}"\n\t{err_name}: {err}"""
            return s.format(path=path, err_name=e.__class__.__name__, err=e)

        module_name = os.path.splitext(os.path.basename(full_path))[0]
        dir_path = os.path.dirname(full_path)
        err_str = ""
        local_stdout = io.BytesIO()
        old_stdout = sys.stdout
        sys.stdout = local_stdout
        sys.exc_clear()

        try:
            module = _import_module(module_name, dir_path)
            module.main(self)
        except ImportError as e:
            err_str += format_error(full_path, e)
        except:  # noqa: E722
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            err_str += traceback.format_exc()
            err_str += format_error(full_path, exc_type(exc_value))
        finally:
            sys.exc_clear()
            sys.stdout = old_stdout
            local_stdout.close()

        return local_stdout.getvalue() + err_str

    def cmd_hide_show_bar(self, position="all"):
        """Toggle visibility of a given bar

        Parameters
        ==========
        position :
            one of: "top", "bottom", "left", "right", or "all" (default: "all")
        """
        if position in ["top", "bottom", "left", "right"]:
            bar = getattr(self.current_screen, position)
            if bar:
                bar.show(not bar.is_show())
                self.current_group.layout_all()
            else:
                logger.warning(
                    "Not found bar in position '%s' for hide/show." % position)
        elif position == "all":
            screen = self.current_screen
            is_show = None
            for bar in [screen.left, screen.right, screen.top, screen.bottom]:
                if bar:
                    if is_show is None:
                        is_show = not bar.is_show()
                    bar.show(is_show)
            if is_show is not None:
                self.current_group.layout_all()
            else:
                logger.warning("Not found bar for hide/show.")
        else:
            logger.error("Invalid position value:{0:s}".format(position))

    def cmd_get_state(self):
        """Get pickled state for restarting qtile"""
        buf = io.BytesIO()
        pickle.dump(QtileState(self), buf, protocol=0)
        state = buf.getvalue().decode()
        logger.debug('State = ')
        logger.debug(''.join(state.split('\n')))
        return state

    def cmd_tracemalloc_toggle(self):
        """Toggle tracemalloc status

        Running tracemalloc is required for qtile-top
        """
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        else:
            tracemalloc.stop()

    def cmd_tracemalloc_dump(self):
        """Dump tracemalloc snapshot"""
        import tracemalloc

        if not tracemalloc.is_tracing():
            return [False, "Trace not started"]
        cache_directory = get_cache_dir()
        malloc_dump = os.path.join(cache_directory, "qtile_tracemalloc.dump")
        tracemalloc.take_snapshot().dump(malloc_dump)
        return [True, malloc_dump]

    def cmd_get_test_data(self):
        """
        Returns any content arbitrarily set in the self.test_data attribute.
        Useful in tests.
        """
        return self.test_data

    def cmd_run_extension(self, extension):
        """Run extensions"""
        extension.run()
