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

from __future__ import annotations

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
from typing import TYPE_CHECKING

import libqtile
from libqtile import bar, hook, ipc, utils
from libqtile.backend import base
from libqtile.command import interface
from libqtile.command.base import CommandError, CommandException, CommandObject
from libqtile.command.client import InteractiveCommandClient
from libqtile.command.interface import IPCCommandServer, QtileCommandInterface
from libqtile.config import Click, Drag, Key, KeyChord, Match, Rule
from libqtile.config import ScratchPad as ScratchPadConfig
from libqtile.config import Screen
from libqtile.core.lifecycle import lifecycle
from libqtile.core.loop import LoopContext, QtileEventLoopPolicy
from libqtile.core.state import QtileState
from libqtile.dgroups import DGroups
from libqtile.extension.base import _Extension
from libqtile.group import _Group
from libqtile.log_utils import logger
from libqtile.scratchpad import ScratchPad
from libqtile.utils import get_cache_dir, lget, send_notification
from libqtile.widget.base import _Widget

if TYPE_CHECKING:
    from typing import Any, Callable

    from typing_extensions import Literal

    from libqtile.command.base import ItemT
    from libqtile.layout.base import Layout


class Qtile(CommandObject):
    """This object is the `root` of the command graph"""

    current_screen: Screen
    dgroups: DGroups
    _eventloop: asyncio.AbstractEventLoop

    def __init__(
        self,
        kore: base.Core,
        config,  # mypy doesn't like the config's dynamic attributes
        no_spawn: bool = False,
        state: str | None = None,
        socket_path: str | None = None,
    ):
        self.core = kore
        self.config = config
        self.no_spawn = no_spawn
        self._state: QtileState | str | None = state
        self.socket_path = socket_path

        self._drag: tuple | None = None
        self.mouse_map: dict[int, list[Click | Drag]] = {}

        self.windows_map: dict[int, base.WindowType] = {}
        self.widgets_map: dict[str, _Widget] = {}
        self.renamed_widgets: list[str]
        self.groups_map: dict[str, _Group] = {}
        self.groups: list[_Group] = []

        self.keys_map: dict[tuple[int, int], Key | KeyChord] = {}
        self.chord_stack: list[KeyChord] = []

        self.screens: list[Screen] = []

        libqtile.init(self)

        self._stopped_event: asyncio.Event | None = None

        self.server = IPCCommandServer(self)

    def load_config(self, initial=False) -> None:
        try:
            self.config.load()
            self.config.validate()
        except Exception as e:
            send_notification("Configuration error", str(e))

        if hasattr(self.core, "wmname"):
            self.core.wmname = getattr(self.config, "wmname", "qtile")  # type: ignore

        self.dgroups = DGroups(self, self.config.groups, self.config.dgroups_key_binder)

        _Widget.global_defaults = self.config.widget_defaults
        _Extension.global_defaults = self.config.extension_defaults

        for installed_extension in _Extension.installed_extensions:
            installed_extension._configure(self)

        for i in self.groups:
            self.groups_map[i.name] = i

        for grp in self.config.groups:
            if isinstance(grp, ScratchPadConfig):
                sp = ScratchPad(grp.name, grp.dropdowns, grp.label, grp.single)
                sp._configure([self.config.floating_layout], self.config.floating_layout, self)
                self.groups.append(sp)
                self.groups_map[sp.name] = sp

        self._process_screens(reloading=not initial)

        # Map and Grab keys
        for key in self.config.keys:
            self.grab_key(key)

        for button in self.config.mouse:
            self.grab_button(button)

        # no_spawn is set after the very first startup; we only want to run the
        # startup hook once.
        if not self.no_spawn:
            hook.fire("startup_once")
            self.no_spawn = True
        hook.fire("startup")

        if self._state:
            if isinstance(self._state, str):
                try:
                    with open(self._state, "rb") as f:
                        st = pickle.load(f)
                        st.apply(self)
                except:  # noqa: E722
                    logger.exception("failed restoring state")
                finally:
                    os.remove(self._state)
            else:
                self._state.apply(self)

        self.core.distribute_windows(initial)

        if self._state:
            for screen in self.screens:
                screen.group.layout.show(screen.get_rect())
                screen.group.layout_all()
        self._state = None
        self.update_desktops()
        hook.subscribe.setgroup(self.update_desktops)

        if self.config.reconfigure_screens:
            hook.subscribe.screen_change(self.cmd_reconfigure_screens)

        if initial:
            hook.fire("startup_complete")

    def _prepare_socket_path(
        self,
        socket_path: str | None = None,
    ) -> str:
        if socket_path is None:
            socket_path = ipc.find_sockfile(self.core.display_name)

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        return socket_path

    def loop(self) -> None:
        asyncio.run(self.async_loop())

    async def async_loop(self) -> None:
        """Run the event loop

        Finalizes the Qtile instance on exit.
        """
        self._eventloop = asyncio.get_running_loop()
        # Set the event loop policy to facilitate access to main event loop
        asyncio.set_event_loop_policy(QtileEventLoopPolicy(self))
        self._stopped_event = asyncio.Event()
        self.core.setup_listener(self)
        try:
            async with LoopContext(
                {
                    signal.SIGTERM: self.stop,
                    signal.SIGINT: self.stop,
                    signal.SIGHUP: self.stop,
                    signal.SIGUSR1: self.cmd_reload_config,
                    signal.SIGUSR2: self.cmd_restart,
                }
            ), ipc.Server(
                self._prepare_socket_path(self.socket_path),
                self.server.call,
            ):
                self.load_config(initial=True)
                await self._stopped_event.wait()
        finally:
            self.finalize()
            self.core.remove_listener()

    def stop(self) -> None:
        hook.fire("shutdown")
        lifecycle.behavior = lifecycle.behavior.TERMINATE
        self.core.graceful_shutdown()
        self._stop()

    def restart(self) -> None:
        hook.fire("restart")
        lifecycle.behavior = lifecycle.behavior.RESTART
        state_file = os.path.join(tempfile.gettempdir(), "qtile-state")
        with open(state_file, "wb") as f:
            self.dump_state(f)
        lifecycle.state_file = state_file
        self._stop()

    def _stop(self) -> None:
        logger.debug("Stopping qtile")
        if self._stopped_event is not None:
            self._stopped_event.set()

    def dump_state(self, buf) -> None:
        try:
            pickle.dump(QtileState(self), buf, protocol=0)
        except:  # noqa: E722
            logger.exception("Unable to pickle qtile state")

    def cmd_reload_config(self) -> None:
        """
        Reload the configuration file.

        Can also be triggered by sending Qtile a SIGUSR1 signal.
        """
        logger.debug("Reloading the configuration file")

        try:
            self.config.load()
        except Exception as error:
            logger.error("Configuration error: {}".format(error))
            send_notification("Configuration error", str(error))
            return

        self._state = QtileState(self, restart=False)
        self._finalize_configurables()
        hook.clear()
        self.ungrab_keys()
        self.chord_stack.clear()
        self.core.ungrab_buttons()
        self.mouse_map.clear()
        self.groups_map.clear()
        self.groups.clear()
        self.screens.clear()
        self.load_config()

    def _finalize_configurables(self) -> None:
        """
        Finalize objects that are instantiated within the config file. In addition to
        shutdown, these are finalized and then regenerated when reloading the config.
        """
        try:
            for widget in self.widgets_map.values():
                widget.finalize()
            self.widgets_map.clear()

            # For layouts we need to finalize each clone of a layout in each group
            for group in self.groups:
                for layout in group.layouts:
                    layout.finalize()

            for screen in self.screens:
                for gap in screen.gaps:
                    gap.finalize()
        except:  # noqa: E722
            logger.exception("exception during finalize")
        hook.clear()

    def finalize(self) -> None:
        self._finalize_configurables()
        self.core.finalize()

    def _process_screens(self, reloading=False) -> None:
        current_groups = [s.group for s in self.screens if hasattr(s, "group")]
        screens = []

        if hasattr(self.config, "fake_screens"):
            screen_info = [(s.x, s.y, s.width, s.height) for s in self.config.fake_screens]
            config = self.config.fake_screens
        else:
            # Alias screens with the same x and y coordinates, taking largest
            xywh = {}  # type: dict[tuple[int, int], tuple[int, int]]
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

            if not hasattr(self, "current_screen") or reloading:
                self.current_screen = scr
                reloading = False

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
            reconfigure_gaps = (x, y, w, h) != (scr.x, scr.y, scr.width, scr.height)
            scr._configure(self, i, x, y, w, h, grp, reconfigure_gaps=reconfigure_gaps)
            screens.append(scr)

        for screen in self.screens:
            if screen not in screens:
                for gap in screen.gaps:
                    if isinstance(gap, bar.Bar) and gap.window:
                        gap.kill_window()

        self.screens = screens

    def cmd_reconfigure_screens(self, ev: Any = None) -> None:
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

        hook.fire("screens_reconfigured")

    def paint_screen(self, screen: Screen, image_path: str, mode: str | None = None) -> None:
        self.core.painter.paint(screen, image_path, mode)

    def process_key_event(self, keysym: int, mask: int) -> None:
        key = self.keys_map.get((keysym, mask), None)
        if key is None:
            logger.debug(
                "Ignoring unknown keysym: {keysym}, mask: {mask}".format(keysym=keysym, mask=mask)
            )
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

    def grab_key(self, key: Key | KeyChord) -> None:
        """Grab the given key event"""
        keysym, mask_key = self.core.grab_key(key)
        self.keys_map[(keysym, mask_key)] = key

    def ungrab_key(self, key: Key | KeyChord) -> None:
        """Ungrab a given key event"""
        keysym, mask_key = self.core.ungrab_key(key)
        self.keys_map.pop((keysym, mask_key))

    def ungrab_keys(self) -> None:
        """Ungrab all key events"""
        self.core.ungrab_keys()
        self.keys_map.clear()

    def grab_chord(self, chord: KeyChord) -> None:
        self.chord_stack.append(chord)
        if self.chord_stack:
            hook.fire("enter_chord", chord.mode)

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

    def grab_button(self, button: Click | Drag) -> None:
        """Grab the given mouse button event"""
        try:
            button.modmask = self.core.grab_button(button)
        except utils.QtileError:
            logger.warning(f"Unknown modifier(s): {button.modifiers}")
            return
        if button.button_code not in self.mouse_map:
            self.mouse_map[button.button_code] = []
        self.mouse_map[button.button_code].append(button)

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

    def add_group(
        self,
        name: str,
        layout: str | None = None,
        layouts: list[Layout] | None = None,
        label: str | None = None,
    ) -> bool:
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

    def delete_group(self, name: str) -> None:
        # one group per screen is needed
        if len(self.groups) == len(self.screens):
            raise ValueError("Can't delete all groups.")
        if name in self.groups_map.keys():
            group = self.groups_map[name]
            if group.screen and hasattr(group.screen, "previous_group"):
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
            del self.groups_map[name]
            hook.fire("delgroup", name)
            hook.fire("changegroup")
            self.update_desktops()

    def register_widget(self, w: _Widget) -> None:
        """
        Register a bar widget

        If a widget with the same name already exists, the new widget will be
        automatically renamed by appending numeric suffixes. For example, if
        the widget is named "foo", we will attempt "foo_1", "foo_2", and so on,
        until a free name is found.

        This naming convention is only used for qtile.widgets_map as every widget
        MUST be registered here to ensure that objects are finalised correctly.

        Widgets can still be accessed by their name when using
        lazy.screen.widget[name] or lazy.bar["top"].widget[name] unless there are
        duplicate widgets in the bar/screen.

        A warning will be provided where renaming has occurred.
        """
        # Find unoccupied name by appending numeric suffixes
        name = w.name
        i = 0
        while name in self.widgets_map:
            i += 1
            name = f"{w.name}_{i}"

        if name != w.name:
            self.renamed_widgets.append(name)

        self.widgets_map[name] = w

    @property
    def current_layout(self) -> Layout:
        return self.current_group.layout

    @property
    def current_group(self) -> _Group:
        return self.current_screen.group

    @property
    def current_window(self) -> base.Window | None:
        return self.current_screen.group.current_window

    def reserve_space(
        self,
        reserved_space: tuple[int, int, int, int],  # [left, right, top, bottom]
        screen: Screen,
    ) -> None:
        """
        Reserve some space at the edge(s) of a screen.
        """
        for i, pos in enumerate(["left", "right", "top", "bottom"]):
            if reserved_space[i]:
                gap = getattr(screen, pos)
                if isinstance(gap, bar.Bar):
                    gap.adjust_for_strut(reserved_space[i])
                elif isinstance(gap, bar.Gap):
                    gap.size += reserved_space[i]
                    if gap.size <= 0:
                        setattr(screen, pos, None)
                else:
                    setattr(screen, pos, bar.Gap(reserved_space[i]))
        screen.resize()

    def free_reserved_space(
        self,
        reserved_space: tuple[int, int, int, int],  # [left, right, top, bottom]
        screen: Screen,
    ):
        """
        Free up space that has previously been reserved at the edge(s) of a screen.
        """
        # mypy can't work out that the new tuple is also length 4 (see mypy #7509)
        self.reserve_space(tuple(-i for i in reserved_space), screen)  # type: ignore

    def manage(self, win: base.WindowType) -> None:
        if isinstance(win, base.Internal):
            self.windows_map[win.wid] = win
            return

        if win.wid in self.windows_map:
            return

        hook.fire("client_new", win)

        # Window may be defunct because
        # it's been declared static in hook.
        if win.defunct:
            return
        self.windows_map[win.wid] = win
        if self.current_screen and isinstance(win, base.Window):
            # Window may have been bound to a group in the hook.
            if not win.group and self.current_screen.group:
                self.current_screen.group.add(win, focus=win.can_steal_focus)
        self.core.update_client_list(self.windows_map)
        hook.fire("client_managed", win)

    def unmanage(self, wid: int) -> None:
        c = self.windows_map.get(wid)
        if c:
            hook.fire("client_killed", c)
            if isinstance(c, base.Static):
                if c.reserved_space:
                    self.free_reserved_space(c.reserved_space, c.screen)
            elif isinstance(c, base.Window):
                if c.group:
                    c.group.remove(c)
            del self.windows_map[wid]
            self.core.update_client_list(self.windows_map)

    def find_screen(self, x: int, y: int) -> Screen | None:
        """Find a screen based on the x and y offset"""
        result = []
        for i in self.screens:
            if i.x <= x <= i.x + i.width and i.y <= y <= i.y + i.height:
                result.append(i)
        if len(result) == 1:
            return result[0]
        return None

    def find_closest_screen(self, x: int, y: int) -> Screen:
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

    def _find_closest_closest(self, x: int, y: int, candidate_screens: list[Screen]) -> Screen:
        """
        if find_closest_screen can't determine one, we've got multiple
        screens, so figure out who is closer.  We'll calculate using
        the square of the distance from the center of a screen.

        Note that this could return None if x, y is right/below all
        screens.
        """
        closest_distance: float | None = None
        if not candidate_screens:
            # try all screens
            candidate_screens = self.screens
        # if left corner is below and right of screen
        # it can't really be a candidate
        candidate_screens = [
            s for s in candidate_screens if x < s.x + s.width and y < s.y + s.height
        ]
        closest_screen = lget(candidate_screens, 0)
        for s in candidate_screens:
            middle_x = s.x + s.width / 2
            middle_y = s.y + s.height / 2
            distance = (x - middle_x) ** 2 + (y - middle_y) ** 2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_screen = s
        return closest_screen or self.screens[0]

    def process_button_click(self, button_code: int, modmask: int, x: int, y: int) -> bool:
        handled = False
        for m in self.mouse_map.get(button_code, []):
            if not m.modmask == modmask:
                continue

            if isinstance(m, Click):
                for i in m.commands:
                    if i.check(self):
                        status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                        if status in (interface.ERROR, interface.EXCEPTION):
                            logger.error("Mouse command error %s: %s" % (i.name, val))
                        handled = True
            elif isinstance(m, Drag):
                if m.start:
                    i = m.start
                    status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("Mouse command error %s: %s" % (i.name, val))
                        continue
                else:
                    val = (0, 0)
                self._drag = (x, y, val[0], val[1], m.commands)
                self.core.grab_pointer()
                handled = True

        return handled

    def process_button_release(self, button_code: int, modmask: int) -> bool:
        if self._drag is not None:
            for m in self.mouse_map.get(button_code, []):
                if isinstance(m, Drag):
                    self._drag = None
                    self.core.ungrab_pointer()
                    return True
        return False

    def process_button_motion(self, x: int, y: int) -> None:
        if self._drag is None:
            return
        ox, oy, rx, ry, cmd = self._drag
        dx = x - ox
        dy = y - oy
        if dx or dy:
            for i in cmd:
                if i.check(self):
                    status, val = self.server.call(
                        (i.selectors, i.name, i.args + (rx + dx, ry + dy), i.kwargs)
                    )
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("Mouse command error %s: %s" % (i.name, val))

    def warp_to_screen(self) -> None:
        if self.current_screen:
            scr = self.current_screen
            self.core.warp_pointer(scr.x + scr.dwidth // 2, scr.y + scr.dheight // 2)

    def focus_screen(self, n: int, warp: bool = True) -> None:
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

    def move_to_group(self, group: str) -> None:
        """Create a group if it doesn't exist and move
        the current window there"""
        if self.current_window and group:
            self.add_group(group)
            self.current_window.togroup(group)

    def _items(self, name: str) -> ItemT:
        if name == "group":
            return True, list(self.groups_map.keys())
        elif name == "layout":
            return True, list(range(len(self.current_group.layouts)))
        elif name == "widget":
            return False, list(self.widgets_map.keys())
        elif name == "bar":
            return False, [x.position for x in self.current_screen.gaps]
        elif name == "window":
            windows: list[str | int]
            windows = [
                k
                for k, v in self.windows_map.items()
                if isinstance(v, CommandObject) and not isinstance(v, _Widget)
            ]
            return True, windows
        elif name == "screen":
            return True, list(range(len(self.screens)))
        elif name == "core":
            return True, []
        return None

    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        if name == "group":
            if sel is None:
                return self.current_group
            else:
                return self.groups_map.get(sel)  # type: ignore
        elif name == "layout":
            if sel is None:
                return self.current_group.layout
            else:
                return utils.lget(self.current_group.layouts, sel)
        elif name == "widget":
            return self.widgets_map.get(sel)  # type: ignore
        elif name == "bar":
            return getattr(self.current_screen, sel)  # type: ignore
        elif name == "window":
            if sel is None:
                return self.current_window
            else:
                windows: dict[str | int, base._Window]
                windows = {
                    k: v
                    for k, v in self.windows_map.items()
                    if isinstance(v, CommandObject) and not isinstance(v, _Widget)
                }
                return windows.get(sel)
        elif name == "screen":
            if sel is None:
                return self.current_screen
            else:
                return utils.lget(self.screens, sel)
        elif name == "core":
            return self.core
        return None

    def call_soon(self, func: Callable, *args) -> asyncio.Handle:
        """A wrapper for the event loop's call_soon which also flushes the core's
        event queue after func is called."""

        def f():
            func(*args)
            self.core.flush()

        return self._eventloop.call_soon(f)

    def call_soon_threadsafe(self, func: Callable, *args) -> asyncio.Handle:
        """Another event loop proxy, see `call_soon`."""

        def f():
            func(*args)
            self.core.flush()

        return self._eventloop.call_soon_threadsafe(f)

    def call_later(self, delay, func: Callable, *args) -> asyncio.TimerHandle:
        """Another event loop proxy, see `call_soon`."""

        def f():
            func(*args)
            self.core.flush()

        return self._eventloop.call_later(delay, f)

    def run_in_executor(self, func: Callable, *args):
        """A wrapper for running a function in the event loop's default
        executor."""
        return self._eventloop.run_in_executor(None, func, *args)

    def cmd_debug(self) -> None:
        """Set log level to DEBUG"""
        logger.setLevel(logging.DEBUG)
        logger.debug("Switching to DEBUG threshold")

    def cmd_info(self) -> None:
        """Set log level to INFO"""
        logger.setLevel(logging.INFO)
        logger.info("Switching to INFO threshold")

    def cmd_warning(self) -> None:
        """Set log level to WARNING"""
        logger.setLevel(logging.WARNING)
        logger.warning("Switching to WARNING threshold")

    def cmd_error(self) -> None:
        """Set log level to ERROR"""
        logger.setLevel(logging.ERROR)
        logger.error("Switching to ERROR threshold")

    def cmd_critical(self) -> None:
        """Set log level to CRITICAL"""
        logger.setLevel(logging.CRITICAL)
        logger.critical("Switching to CRITICAL threshold")

    def cmd_loglevel(self) -> int:
        return logger.level

    def cmd_loglevelname(self) -> str:
        return logging.getLevelName(logger.level)

    def cmd_pause(self) -> None:
        """Drops into pdb"""
        import pdb

        pdb.set_trace()

    def cmd_groups(self) -> dict[str, dict[str, Any]]:
        """Return a dictionary containing information for all groups

        Examples
        ========

            groups()
        """
        return {i.name: i.info() for i in self.groups}

    def cmd_display_kb(self, *args) -> str:
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
                format_string = " ".join(
                    "%-{0:d}s".format(max_col_size + 2) for max_col_size in self.max_col_size
                )
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

        def walk_binding(k: Key | KeyChord, mode: str) -> None:
            nonlocal rows
            modifiers, name = ", ".join(k.modifiers), k.key
            if isinstance(k, Key):
                if not k.commands:
                    return
                allargs = ", ".join(
                    [
                        value.__name__ if callable(value) else repr(value)
                        for value in k.commands[0].args
                    ]
                    + [
                        "%s = %s" % (keyword, repr(value))
                        for keyword, value in k.commands[0].kwargs.items()
                    ]
                )
                rows.append(
                    (
                        mode,
                        name,
                        modifiers,
                        "{:s}({:s})".format(k.commands[0].name, allargs),
                        k.desc,
                    )
                )
                return
            if isinstance(k, KeyChord):
                new_mode_s = k.mode if k.mode else "<unnamed>"
                new_mode = (
                    k.mode
                    if mode == "<root>"
                    else "{}>{}".format(mode, k.mode if k.mode else "_")
                )
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

    def cmd_list_widgets(self) -> list[str]:
        """List of all addressible widget names"""
        return list(self.widgets_map.keys())

    def cmd_to_layout_index(self, index: str, name: str | None = None) -> None:
        """Switch to the layout with the given index in self.layouts.

        Parameters
        ==========
        index :
            Index of the layout in the list of layouts.
        name :
            Group name. If not specified, the current group is assumed.
        """
        if name is not None:
            group = self.groups_map[name]
        else:
            group = self.current_group
        group.use_layout(index)

    def cmd_next_layout(self, name: str | None = None) -> None:
        """Switch to the next layout.

        Parameters
        ==========
        name :
            Group name. If not specified, the current group is assumed
        """
        if name is not None:
            group = self.groups_map[name]
        else:
            group = self.current_group
        group.use_next_layout()

    def cmd_prev_layout(self, name: str | None = None) -> None:
        """Switch to the previous layout.

        Parameters
        ==========
        name :
            Group name. If not specified, the current group is assumed
        """
        if name is not None:
            group = self.groups_map[name]
        else:
            group = self.current_group
        group.use_previous_layout()

    def cmd_screens(self) -> list[dict[str, Any]]:
        """Return a list of dictionaries providing information on all screens"""
        lst = [
            dict(
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
                ),
            )
            for i in self.screens
        ]
        return lst

    def cmd_simulate_keypress(self, modifiers, key) -> None:
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
        try:
            self.core.simulate_keypress(modifiers, key)
        except utils.QtileError as e:
            raise CommandError(str(e))

    def cmd_validate_config(self) -> None:
        try:
            self.config.load()
        except Exception as error:
            send_notification("Configuration check", str(error))
        else:
            send_notification("Configuration check", "No error found!")

    def cmd_restart(self) -> None:
        """
        Restart Qtile.

        Can also be triggered by sending Qtile a SIGUSR2 signal.
        """
        if not self.core.supports_restarting:
            raise CommandError(f"Backend does not support restarting: {self.core.name}")

        try:
            self.config.load()
        except Exception as error:
            logger.error("Preventing restart because of a configuration error: {}".format(error))
            send_notification("Configuration error", str(error))
            return
        self.restart()

    def cmd_spawn(self, cmd: str | list[str], shell: bool = False) -> int:
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
                    del os.environ["VIRTUAL_ENV"]
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
            pid = int(os.read(r, 1024))
            os.close(r)
            return pid

    def cmd_status(self) -> Literal["OK"]:
        """Return "OK" if Qtile is running"""
        return "OK"

    def cmd_sync(self) -> None:
        """
        Sync the backend's event queue. Should only be used for development.
        """
        self.core.flush()

    def cmd_to_screen(self, n: int) -> None:
        """Warp focus to screen n, where n is a 0-based screen number

        Examples
        ========

            to_screen(0)
        """
        self.focus_screen(n)

    def cmd_next_screen(self) -> None:
        """Move to next screen"""
        self.focus_screen((self.screens.index(self.current_screen) + 1) % len(self.screens))

    def cmd_prev_screen(self) -> None:
        """Move to the previous screen"""
        self.focus_screen((self.screens.index(self.current_screen) - 1) % len(self.screens))

    def cmd_windows(self) -> list[dict[str, Any]]:
        """Return info for each client window"""
        return [
            i.info()
            for i in self.windows_map.values()
            if not isinstance(i, (base.Internal, _Widget)) and isinstance(i, CommandObject)
        ]

    def cmd_internal_windows(self) -> list[dict[str, Any]]:
        """Return info for each internal window (bars, for example)"""
        return [i.info() for i in self.windows_map.values() if isinstance(i, base.Internal)]

    def cmd_qtile_info(self) -> dict:
        """Returns a dictionary of info on the Qtile instance"""
        return {}

    def cmd_shutdown(self) -> None:
        """Quit Qtile"""
        self.stop()

    def cmd_switch_groups(self, namea: str, nameb: str) -> None:
        """Switch position of two groups by name"""
        if namea not in self.groups_map or nameb not in self.groups_map:
            return

        indexa = self.groups.index(self.groups_map[namea])
        indexb = self.groups.index(self.groups_map[nameb])

        self.groups[indexa], self.groups[indexb] = self.groups[indexb], self.groups[indexa]
        hook.fire("setgroup")

        # update window _NET_WM_DESKTOP
        for group in (self.groups[indexa], self.groups[indexb]):
            for w in group.windows:
                w.group = group

    def find_window(self, wid: int) -> None:
        window = self.windows_map.get(wid)
        if isinstance(window, base.Window) and window.group:
            if not window.group.screen:
                self.current_screen.set_group(window.group)
            window.group.focus(window, False)

    def cmd_findwindow(self, prompt: str = "window", widget: str = "prompt") -> None:
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

        mb.start_input(prompt, self.find_window, "window", strict_completer=True)

    def cmd_next_urgent(self) -> None:
        """Focus next window with urgent hint"""
        try:
            nxt = [w for w in self.windows_map.values() if w.urgent][0]
            assert isinstance(nxt, base.Window)
            if nxt.group:
                nxt.group.cmd_toscreen()
                nxt.group.focus(nxt)
            else:
                self.current_screen.group.add(nxt)
                self.current_screen.group.focus(nxt)
        except IndexError:
            pass  # no window had urgent set

    def cmd_togroup(self, prompt: str = "group", widget: str = "prompt") -> None:
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

    def cmd_switchgroup(self, prompt: str = "group", widget: str = "prompt") -> None:
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
                    logger.warning("No group named '{0:s}' present.".format(group))

        mb = self.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '{0:s}' present.".format(widget))
            return

        mb.start_input(prompt, f, "group", strict_completer=True)

    def cmd_labelgroup(self, prompt: str = "label", widget: str = "prompt") -> None:
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

    def cmd_spawncmd(
        self,
        prompt: str = "spawn",
        widget: str = "prompt",
        command: str = "%s",
        complete: str = "cmd",
        shell: bool = True,
        aliases: dict[str, str] | None = None,
    ) -> None:
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
        shell :
            Execute the command with /bin/sh (default: True)
        aliases :
            Dictionary mapping aliases to commands. If the entered command is a key in
            this dict, the command it maps to will be executed instead.
        """

        def f(args):
            if args:
                if aliases and args in aliases:
                    args = aliases[args]
                self.cmd_spawn(command % args, shell=shell)

        try:
            mb = self.widgets_map[widget]
            mb.start_input(prompt, f, complete)
        except KeyError:
            logger.error("No widget named '{0:s}' present.".format(widget))

    def cmd_qtilecmd(
        self,
        prompt: str = "command",
        widget: str = "prompt",
        messenger: str = "xmessage",
    ) -> None:
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
                    cmd_arg = str(cmd).split(" ")
                except AttributeError:
                    return
                cmd_len = len(cmd_arg)
                if cmd_len == 0:
                    logger.debug("No command entered.")
                    return
                try:
                    result = eval("c.{0:s}".format(cmd))
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

    def cmd_addgroup(
        self,
        group: str,
        label: str | None = None,
        layout: str | None = None,
        layouts: list[Layout] | None = None,
    ) -> bool:
        """Add a group with the given name"""
        return self.add_group(name=group, layout=layout, layouts=layouts, label=label)

    def cmd_delgroup(self, group: str) -> None:
        """Delete a group with the given name"""
        self.delete_group(group)

    def cmd_add_rule(
        self,
        match_args: dict[str, Any],
        rule_args: dict[str, Any],
        min_priorty: bool = False,
    ):
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
            logger.warning("No dgroups created")
            return

        match = Match(**match_args)
        rule = Rule([match], **rule_args)
        return self.dgroups.add_rule(rule, min_priorty)

    def cmd_remove_rule(self, rule_id: int) -> None:
        """Remove a dgroup rule by rule_id"""
        self.dgroups.remove_rule(rule_id)

    def cmd_hide_show_bar(
        self,
        position: Literal["top", "bottom", "left", "right", "all"] = "all",
    ) -> None:
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
                logger.warning("Not found bar in position '%s' for hide/show." % position)
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
            logger.warning("Invalid position value:{0:s}".format(position))

    def cmd_get_state(self) -> str:
        """Get pickled state for restarting qtile"""
        buf = io.BytesIO()
        self.dump_state(buf)
        state = buf.getvalue().decode(errors="backslashreplace")
        logger.debug("State = ")
        logger.debug("".join(state.split("\n")))
        return state

    def cmd_tracemalloc_toggle(self) -> None:
        """Toggle tracemalloc status

        Running tracemalloc is required for `qtile top`
        """
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        else:
            tracemalloc.stop()

    def cmd_tracemalloc_dump(self) -> tuple[bool, str]:
        """Dump tracemalloc snapshot"""
        import tracemalloc

        if not tracemalloc.is_tracing():
            return False, "Trace not started"
        cache_directory = get_cache_dir()
        malloc_dump = os.path.join(cache_directory, "qtile_tracemalloc.dump")
        tracemalloc.take_snapshot().dump(malloc_dump)
        return True, malloc_dump

    def cmd_get_test_data(self) -> Any:
        """
        Returns any content arbitrarily set in the self.test_data attribute.
        Useful in tests.
        """
        return self.test_data  # type: ignore

    def cmd_run_extension(self, extension: _Extension) -> None:
        """Run extensions"""
        extension.run()
