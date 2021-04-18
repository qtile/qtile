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
import io
import logging
import os
import pickle
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Union

import xcffib
import xcffib.xinerama
import xcffib.xproto

import libqtile
from libqtile import confreader, hook, ipc, utils
from libqtile.backend import base
from libqtile.backend.x11 import window
from libqtile.command import interface
from libqtile.command.base import CommandError, CommandException, CommandObject
from libqtile.command.client import InteractiveCommandClient
from libqtile.command.interface import IPCCommandServer, QtileCommandInterface
from libqtile.config import Click, Drag, Key, KeyChord, Match, Rule
from libqtile.config import ScratchPad as ScratchPadConfig
from libqtile.config import Screen
from libqtile.core.lifecycle import lifecycle
from libqtile.core.loop import LoopContext
from libqtile.core.state import QtileState
from libqtile.dgroups import DGroups
from libqtile.extension.base import _Extension
from libqtile.group import _Group
from libqtile.lazy import lazy
from libqtile.log_utils import logger
from libqtile.scratchpad import ScratchPad
from libqtile.utils import get_cache_dir, send_notification
from libqtile.widget.base import _Widget


class Qtile(CommandObject):
    """This object is the `root` of the command graph"""
    def __init__(
        self,
        kore,
        config,
        no_spawn=False,
        state=None,
        socket_path: Optional[str] = None,
    ):
        self.core = kore
        self.no_spawn = no_spawn
        self._state = state
        self.socket_path = socket_path

        self._drag: Optional[Tuple] = None
        self.mouse_map: Dict[Tuple[int, int], List[Union[Click, Drag]]] = {}
        self.mouse_position = (0, 0)

        self.windows_map: Dict[int, base.WindowType] = {}
        self.widgets_map: Dict[str, _Widget] = {}
        self.groups_map: Dict[str, _Group] = {}
        self.groups: List[_Group] = []
        self.dgroups: Optional[DGroups] = None

        self.keys_map: Dict[Tuple[int, int], Union[Key, KeyChord]] = {}
        self.chord_stack: List[KeyChord] = []

        self.current_screen: Optional[Screen] = None
        self.screens: List[Screen] = []

        libqtile.init(self)

        self._eventloop: Optional[asyncio.AbstractEventLoop] = None
        self._stopped_event: Optional[asyncio.Event] = None

        self.server = IPCCommandServer(self)
        self.config = config
        self.load_config()

    def load_config(self):
        try:
            self.config.load()
            self.config.validate()
        except Exception as e:
            logger.exception('Error while reading config file (%s)', e)
            self.config = confreader.Config()
            from libqtile.widget import TextBox
            widgets = self.config.screens[0].bottom.widgets
            widgets.insert(0, TextBox('Config Err!'))

        if hasattr(self.core, "wmname"):
            self.core.wmname = getattr(self.config, "wmname", "qtile")

        self.dgroups = DGroups(self, self.config.groups, self.config.dgroups_key_binder)

        if self.config.widget_defaults:
            _Widget.global_defaults = self.config.widget_defaults
        if self.config.extension_defaults:
            _Extension.global_defaults = self.config.extension_defaults

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

        # It fixes problems with focus when clicking windows of some specific clients like xterm
        def noop(qtile):
            pass
        self.config.mouse += (Click([], "Button1", lazy.function(noop), focus="after"),)

    def dump_state(self, buf):
        try:
            pickle.dump(QtileState(self), buf, protocol=0)
        except:  # noqa: E722
            logger.exception('Unable to pickle qtile state')

    def _configure(self):
        """
        This is the part of init that needs to happen after the event loop is
        fully set up. asyncio is required to listen and respond to backend
        events.
        """
        self._process_screens()
        self.current_screen = self.screens[0]

        # Map and Grab keys
        for key in self.config.keys:
            self.grab_key(key)

        for button in self.config.mouse:
            self.grab_button(button)

        # no_spawn is set when we are restarting; we only want to run the
        # startup hook once.
        if not self.no_spawn:
            hook.fire("startup_once")
        hook.fire("startup")

        if self._state:
            try:
                with open(self._state, 'rb') as f:
                    st = pickle.load(f)
                st.apply(self)
            except:  # noqa: E722
                logger.exception("failed restoring state")
            finally:
                os.remove(self._state)

        self.core.scan()
        if self._state:
            for screen in self.screens:
                screen.group.layout_all()
        self._state = None
        self.update_desktops()
        hook.subscribe.setgroup(self.update_desktops)

        if self.config.reconfigure_screens:
            hook.subscribe.screen_change(self.cmd_reconfigure_screens)

        hook.fire("startup_complete")

    def _prepare_socket_path(
        self,
        socket_path: Optional[str] = None,
    ) -> str:
        if socket_path is None:
            socket_path = ipc.find_sockfile(self.core.display_name)

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        return socket_path

    @property
    def selection(self):
        return self.core._selection

    def loop(self) -> None:
        asyncio.run(self.async_loop())

    async def async_loop(self) -> None:
        """Run the event loop

        Finalizes the Qtile instance on exit.
        """
        self._eventloop = asyncio.get_running_loop()
        self._stopped_event = asyncio.Event()
        self.core.setup_listener(self)
        try:
            async with LoopContext({
                signal.SIGTERM: self.stop,
                signal.SIGINT: self.stop,
                signal.SIGHUP: self.stop,
            }), ipc.Server(
                self._prepare_socket_path(self.socket_path),
                self.server.call,
            ):
                self._configure()
                await self._stopped_event.wait()
        finally:
            self.finalize()
            self.core.remove_listener()

    def stop(self):
        hook.fire("shutdown")
        lifecycle.behavior = lifecycle.behavior.TERMINATE
        self.graceful_shutdown()
        self._stop()

    def restart(self):
        hook.fire("restart")
        lifecycle.behavior = lifecycle.behavior.RESTART
        state_file = os.path.join(tempfile.gettempdir(), 'qtile-state')
        with open(state_file, 'wb') as f:
            self.dump_state(f)
        lifecycle.state_file = state_file
        self._stop()

    def _stop(self):
        logger.debug('Stopping qtile')
        if self._stopped_event is not None:
            self._stopped_event.set()

    def finalize(self):
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
        finally:
            hook.clear()
            self.core.finalize()

    def _process_screens(self) -> None:
        current_groups = [screen.group for screen in self.screens if screen.group]
        self.screens = []

        if hasattr(self.config, 'fake_screens'):
            screen_info = [(s.x, s.y, s.width, s.height) for s in self.config.fake_screens]
            config = self.config.fake_screens
        else:
            # Alias screens with the same x and y coordinates, taking largest
            xywh = {}  # type: Dict[Tuple[int, int], Tuple[int, int]]
            for sx, sy, sw, sh in self.core.get_screen_info():
                pos = (sx, sy)
                width, height = xywh.get(pos, (0, 0))
                xywh[pos] = (max(width, sw), max(height, sh))

            screen_info = [(x, y, w, h) for (x, y), (w, h) in xywh.items()]
            config = self.config.screens

        for i, (x, y, w, h) in enumerate(screen_info):
            if i + 1 > len(config):
                scr = Screen()
            else:
                scr = config[i]

            if not self.current_screen:
                self.current_screen = scr

            if len(self.groups) < i + 1:
                name = f"autogen_{i + 1}"
                self.add_group(name)
                logger.warning(f"Too few groups in config. Added group: {name}")

            if i < len(current_groups):
                grp = current_groups[i]
            else:
                for grp in self.groups:
                    if not grp.screen:
                        break

            scr._configure(self, i, x, y, w, h, grp)
            self.screens.append(scr)

    def cmd_reconfigure_screens(self, ev=None):
        """
        This can be used to set up screens again during run time. Intended usage is to
        be called when the screen_change hook is fired, responding to changes in
        physical monitor setup by configuring qtile.screens accordingly. The ev kwarg is
        ignored; it is here in case this function is hooked directly to screen_change.
        """
        logger.info("Reconfiguring screens.")
        self._process_screens()

        for group in self.groups:
            if group.screen:
                if group.screen in self.screens:
                    group.layout_all()
                else:
                    group.hide()

    def paint_screen(self, screen, image_path, mode=None):
        if hasattr(self.core, "painter"):
            self.core.painter.paint(screen, image_path, mode)

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
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("KB command error %s: %s" % (cmd.name, val))
            if self.chord_stack and (self.chord_stack[-1].mode == "" or key.key == "Escape"):
                self.cmd_ungrab_chord()
            return

    def grab_keys(self) -> None:
        """Re-grab all of the keys configured in the key map

        Useful when a keyboard mapping event is received.
        """
        self.core.ungrab_keys()
        for key in self.keys_map.values():
            self.grab_key(key)

    def grab_key(self, key: Union[Key, KeyChord]) -> None:
        """Grab the given key event"""
        keysym, mask_key = self.core.grab_key(key)
        self.keys_map[(keysym, mask_key)] = key

    def ungrab_key(self, key: Union[Key, KeyChord]) -> None:
        """Ungrab a given key event"""
        keysym, mask_key = self.core.ungrab_key(key)
        self.keys_map.pop((keysym, mask_key))

    def ungrab_keys(self) -> None:
        """Ungrab all key events"""
        self.core.ungrab_keys()
        self.keys_map.clear()

    def grab_chord(self, chord) -> None:
        self.chord_stack.append(chord)
        if self.chord_stack:
            hook.fire("enter_chord", self.chord_stack[-1].mode)

        self.ungrab_keys()
        for key in chord.submappings:
            self.grab_key(key)

    def cmd_ungrab_chord(self) -> None:
        """Leave a chord mode"""
        hook.fire("leave_chord")

        self.ungrab_keys()
        if not self.chord_stack:
            logger.debug("cmd_ungrab_chord was called when no chord mode was active")
            return
        # The first pop is necessary: Otherwise we would be stuck in a mode;
        # we could not leave it: the code below would re-enter the old mode.
        self.chord_stack.pop()
        # Find another named mode or load the root keybindings:
        while self.chord_stack:
            chord = self.chord_stack.pop()
            if chord.mode != "":
                self.grab_chord(chord)
                break
        else:
            for key in self.config.keys:
                self.grab_key(key)

    def cmd_ungrab_all_chords(self) -> None:
        """Leave all chord modes and grab the root bindings"""
        hook.fire("leave_chord")
        self.ungrab_keys()
        self.chord_stack.clear()
        for key in self.config.keys:
            self.grab_key(key)

    def grab_button(self, button: Union[Click, Drag]) -> None:
        """Grab the given mouse button event"""
        try:
            modmask = self.core.grab_button(button)
        except utils.QtileError:
            logger.warning(f"Unknown modifier(s): {button.modifiers}")
            return
        key = (button.button_code, modmask)
        if key not in self.mouse_map:
            self.mouse_map[key] = []
        self.mouse_map[key].append(button)

    def update_desktops(self) -> None:
        try:
            index = self.groups.index(self.current_group)
        # TODO: we should really only except ValueError here, AttributeError is
        # an annoying chicken and egg because we're accessing current_screen
        # (via current_group), and when we set up the initial groups, there
        # aren't any screens yet. This can probably be changed when #475 is
        # fixed.
        except (ValueError, AttributeError):
            index = 0

        self.core.update_desktops(self.groups, index)

    def add_group(self, name, layout=None, layouts=None, label=None):
        if name not in self.groups_map.keys():
            g = _Group(name, layout, label=label)
            self.groups.append(g)
            if not layouts:
                layouts = self.config.layouts
            g._configure(layouts, self.config.floating_layout, self)
            self.groups_map[name] = g
            hook.fire("addgroup", name)
            hook.fire("changegroup")
            self.update_desktops()

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
            hook.fire("delgroup", name)
            hook.fire("changegroup")
            self.update_desktops()

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

    @property
    def current_layout(self):
        return self.current_group.layout

    @property
    def current_group(self):
        return self.current_screen.group

    @property
    def current_window(self):
        return self.current_screen.group.current_window

    def reserve_space(self, reserved_space, screen):
        from libqtile.bar import Bar, Gap

        for i, pos in enumerate(["left", "right", "top", "bottom"]):
            if reserved_space[i]:
                bar = getattr(screen, pos)
                if isinstance(bar, Bar):
                    bar.adjust_for_strut(reserved_space[i])
                elif isinstance(bar, Gap):
                    bar.size += reserved_space[i]
                    if bar.size <= 0:
                        setattr(screen, pos, None)
                else:
                    setattr(screen, pos, Gap(reserved_space[i]))
        screen.resize()

    def free_reserved_space(self, reserved_space, screen):
        self.reserve_space([-i for i in reserved_space], screen)

    def map_window(self, win: base.WindowType) -> None:
        c = self.manage(win)
        if c and (not c.group or not c.group.screen):
            return
        win.window.map()

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

    def manage(self, win: base.WindowType):
        if isinstance(win, base.Internal):
            self.windows_map[win.wid] = win

        if win.wid in self.windows_map:
            return self.windows_map[win.wid]

        hook.fire("client_new", win)

        # Window may be defunct because
        # it's been declared static in hook.
        if win.defunct:
            return
        self.windows_map[win.wid] = win
        # Window may have been bound to a group in the hook.
        if not win.group:
            self.current_screen.group.add(win, focus=win.can_steal_focus())
        self.core.update_client_list(self.windows_map)
        hook.fire("client_managed", win)
        return win

    def unmanage(self, win):
        c = self.windows_map.get(win)
        if c:
            hook.fire("client_killed", c)
            if isinstance(c, base.Static):
                self.free_reserved_space(c.reserved_space, c.screen)
            if getattr(c, "group", None):
                c.group.remove(c)
            del self.windows_map[win]
            self.core.update_client_list(self.windows_map)

    def graceful_shutdown(self):
        """
        Try and gracefully shutdown windows before exiting with SIGTERM, vs.
        just closing the X session and having the X server send them all
        SIGKILL.
        """

        def get_interesting_pid(win):
            # We don't need to kill Internal or Static windows, they're qtile
            # managed and don't have any state.
            if not isinstance(win, base.Window):
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

    def _focus_by_click(self, e):
        """Bring a window to the front

        Parameters
        ==========
        e : xcb event
            Click event used to determine window to focus
        """
        if e.child:
            wid = e.child
            window = self.windows_map.get(wid)

            if self.config.bring_front_click and (
                self.config.bring_front_click != "floating_only" or getattr(window, "floating", False)
            ):
                self.core.conn.conn.core.ConfigureWindow(
                    wid, xcffib.xproto.ConfigWindow.StackMode, [xcffib.xproto.StackMode.Above]
                )

            try:
                if window.group.screen is not self.current_screen:
                    self.focus_screen(window.group.screen.index, warp=False)
                self.current_group.focus(window, False)
                window.focus(False)
            except AttributeError:
                # probably clicked an internal window
                screen = self.find_screen(e.root_x, e.root_y)
                if screen:
                    self.focus_screen(screen.index, warp=False)

        else:
            # clicked on root window
            screen = self.find_screen(e.root_x, e.root_y)
            if screen:
                self.focus_screen(screen.index, warp=False)

        self.core.conn.conn.core.AllowEvents(xcffib.xproto.Allow.ReplayPointer, e.time)
        self.core.conn.conn.flush()

    def process_button_click(self, button_code, modmask, x, y, event) -> None:
        self.mouse_position = (x, y)
        for m in self.mouse_map.get((button_code, modmask), []):
            if isinstance(m, Click):
                for i in m.commands:
                    if i.check(self):
                        if m.focus == "before":
                            self._focus_by_click(event)
                        status, val = self.server.call(
                            (i.selectors, i.name, i.args, i.kwargs))
                        if m.focus == "after":
                            self._focus_by_click(event)
                        if status in (interface.ERROR, interface.EXCEPTION):
                            logger.error(
                                "Mouse command error %s: %s" % (i.name, val)
                            )
            elif isinstance(m, Drag):
                if m.start:
                    i = m.start
                    if m.focus == "before":
                        self._focus_by_click(event)
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args, i.kwargs))
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )
                        continue
                else:
                    val = (0, 0)
                if m.focus == "after":
                    self._focus_by_click(event)
                self._drag = (x, y, val[0], val[1], m.commands)
                self.core.grab_pointer()

    def process_button_release(self, button_code, modmask):
        k = self.mouse_map.get((button_code, modmask))
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
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error(
                            "Mouse command error %s: %s" % (i.name, val)
                        )

    def warp_to_screen(self):
        if self.current_screen:
            scr = self.current_screen
            self.core.warp_pointer(scr.x + scr.dwidth // 2, scr.y + scr.dheight // 2)

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
            if self.current_window is None and warp:
                self.warp_to_screen()

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
        return [i.wid for i in self.windows_map.values()]

    def client_from_wid(self, wid):
        for i in self.windows_map.values():
            if i.wid == wid:
                return i
        return None

    def call_soon(self, func, *args):
        """ A wrapper for the event loop's call_soon which also flushes the X
        event queue to the server after func is called. """
        def f():
            func(*args)
            self.core.conn.flush()
        return self._eventloop.call_soon(f)

    def call_soon_threadsafe(self, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        def f():
            func(*args)
            self.core.conn.flush()
        return self._eventloop.call_soon_threadsafe(f)

    def call_later(self, delay, func, *args):
        """ Another event loop proxy, see `call_soon`. """
        def f():
            func(*args)
            self.core.conn.flush()
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
        result.add(["Mode", "KeySym", "Mod", "Command", "Desc"])
        result.add([])
        rows = []

        def walk_binding(k: Union[Key, KeyChord], mode: str) -> None:
            nonlocal rows
            modifiers, name = ", ".join(k.modifiers), k.key
            if isinstance(k, Key):
                if not k.commands:
                    return
                allargs = ", ".join(
                    [value.__name__ if callable(value) else repr(value)
                     for value in k.commands[0].args] +
                    ["%s = %s" % (keyword, repr(value)) for keyword, value in k.commands[0].kwargs.items()]
                )
                rows.append((mode, name, modifiers,
                             "{:s}({:s})".format(k.commands[0].name, allargs), k.desc))
                return
            if isinstance(k, KeyChord):
                new_mode_s = k.mode if k.mode else "<unnamed>"
                new_mode = (k.mode if mode == "<root>" else
                            "{}>{}".format(mode, k.mode if k.mode else "_"))
                rows.append((mode, name, modifiers, "", "Enter {:s} mode".format(new_mode_s)))
                for s in k.submappings:
                    walk_binding(s, new_mode)
                return
            raise TypeError("Unexpected type: {}".format(type(k)))

        for k in self.config.keys:
            walk_binding(k, "<root>")
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
        if hasattr(self.core, 'simulate_keypress'):
            try:
                self.core.simulate_keypress(modifiers, key)
            except utils.QtileError as e:
                raise CommandError(str(e))
        else:
            raise CommandError("Backend does not support simulating keypresses")

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

    def cmd_spawn(self, cmd, shell=False):
        """Run cmd, in a shell or not (default).

        cmd may be a string or a list (similar to subprocess.Popen).

        Examples
        ========

            spawn("firefox")

            spawn(["xterm", "-T", "Temporary terminal"])
        """
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = list(cmd)
            cmd = subprocess.list2cmdline(args)

        to_lookup = args[0]
        if shell:
            args = ["/bin/sh", "-c", cmd]

        if shutil.which(to_lookup) is None:
            logger.error("couldn't find `{}`".format(to_lookup))
            return -1

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
                except OSError:
                    # can't log here since we forked :(
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
        """Return "OK" if Qtile is running"""
        return "OK"

    def cmd_sync(self):
        """Sync the X display. Should only be used for development"""
        self.core.conn.flush()

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
            if not isinstance(i, base.Internal)
        ]

    def cmd_internal_windows(self):
        """Return info for each internal window (bars, for example)"""
        return [
            i.info() for i in self.windows_map.values()
            if isinstance(i, base.Internal)
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

    def cmd_labelgroup(self, prompt="label", widget="prompt"):
        """Launch prompt widget to label the current group

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "label")
        widget :
            Name of the prompt widget (default: "prompt")
        """
        def f(name):
            self.current_group.cmd_set_label(name or None)

        try:
            mb = self.widgets_map[widget]
            mb.start_input(prompt, f, allow_empty_input=True)
        except KeyError:
            logger.error("No widget named '{0:s}' present.".format(widget))

    def cmd_spawncmd(self, prompt="spawn", widget="prompt",
                     command="%s", complete="cmd", shell=True):
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
                self.cmd_spawn(command % args, shell=shell)
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
            If the rule is added with minimum priority (last) (default: False)
        """
        if not self.dgroups:
            logger.warning('No dgroups created')
            return

        match = Match(**match_args)
        rule = Rule([match], **rule_args)
        return self.dgroups.add_rule(rule, min_priorty)

    def cmd_remove_rule(self, rule_id):
        """Remove a dgroup rule by rule_id"""
        self.dgroups.remove_rule(rule_id)

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
        self.dump_state(buf)
        state = buf.getvalue().decode(errors="backslashreplace")
        logger.debug('State = ')
        logger.debug(''.join(state.split('\n')))
        return state

    def cmd_tracemalloc_toggle(self):
        """Toggle tracemalloc status

        Running tracemalloc is required for `qtile top`
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
