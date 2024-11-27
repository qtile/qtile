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
import faulthandler
import io
import logging
import os
import pickle
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

import libqtile
from libqtile import bar, hook, ipc, utils
from libqtile.backend import base
from libqtile.command import interface
from libqtile.command.base import CommandError, CommandException, CommandObject, expose_command
from libqtile.command.client import InteractiveCommandClient
from libqtile.command.interface import IPCCommandServer, QtileCommandInterface
from libqtile.config import Click, Drag, Key, KeyChord, Match, Mouse, Rule, Screen, ScreenRect
from libqtile.config import ScratchPad as ScratchPadConfig
from libqtile.core.lifecycle import lifecycle
from libqtile.core.loop import LoopContext, QtileEventLoopPolicy
from libqtile.core.state import QtileState
from libqtile.dgroups import DGroups
from libqtile.extension.base import _Extension
from libqtile.group import _Group
from libqtile.log_utils import logger
from libqtile.resources.sleep import inhibitor
from libqtile.scratchpad import ScratchPad
from libqtile.scripts.main import VERSION
from libqtile.utils import cancel_tasks, get_cache_dir, lget, remove_dbus_rules, send_notification
from libqtile.widget.base import _Widget

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Literal

    from libqtile.command.base import ItemT
    from libqtile.confreader import Config
    from libqtile.layout.base import Layout
    from libqtile.utils import ColorType


class Qtile(CommandObject):
    """This object is the `root` of the command graph"""

    current_screen: Screen
    dgroups: DGroups
    _eventloop: asyncio.AbstractEventLoop

    def __init__(
        self,
        kore: base.Core,
        config: Config,
        no_spawn: bool = False,
        state: str | None = None,
        socket_path: str | None = None,
    ) -> None:
        self.core: base.Core = kore
        self.config = config
        self.no_spawn = no_spawn
        self._state: QtileState | str | None = state
        self.socket_path = socket_path

        self._drag: tuple | None = None
        self._mouse_map: defaultdict[int, list[Mouse]] = defaultdict(list)

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

    def load_config(self, initial: bool = False) -> None:
        try:
            self.config.load()
            self.config.validate()
        except Exception as e:
            logger.exception("Configuration error:")
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

        self.core.on_config_load(initial)

        if self._state:
            for screen in self.screens:
                screen.group.layout.show(screen.get_rect())
                screen.group.layout_all()
        self._state = None
        self.update_desktops()
        hook.subscribe.setgroup(self.update_desktops)

        if self.config.reconfigure_screens:
            hook.subscribe.screen_change(self.reconfigure_screens)

        # Start the sleep inhibitor process to listen to sleep signals
        # NB: the inhibitor will only connect to the dbus service if the
        # user has used the "suspend" or "resume" hooks in their config.
        inhibitor.start()

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
        self.core.qtile = self
        self.load_config(initial=True)
        self.core.setup_listener()

        faulthandler.enable(all_threads=True)
        faulthandler.register(signal.SIGUSR2, all_threads=True)

        try:
            signals = {
                signal.SIGTERM: self.stop,
                signal.SIGINT: self.stop,
                signal.SIGHUP: self.stop,
                signal.SIGUSR1: self.reload_config,
            }
            if self.core.name == "x11":
                # the wayland backend installs its own SIGCHLD handler after
                # the XWayland X server has initialized (as a workaround). the
                # x11 backend can just do it here.
                signals[signal.SIGCHLD] = utils.reap_zombies
            async with (
                LoopContext(signals),
                ipc.Server(
                    self._prepare_socket_path(self.socket_path),
                    self.server.call,
                ),
            ):
                await self._stopped_event.wait()
        finally:
            self.finalize()
            self.core.remove_listener()

    def stop(self, exitcode: int = 0) -> None:
        hook.fire("shutdown")
        lifecycle.behavior = lifecycle.behavior.TERMINATE
        lifecycle.exitcode = exitcode
        self.core.graceful_shutdown()
        self._stop()

    @expose_command()
    def restart(self) -> None:
        """Restart Qtile.

        Can also be triggered by sending Qtile a SIGUSR2 signal.
        """
        if not self.core.supports_restarting:
            raise CommandError(f"Backend does not support restarting: {self.core.name}")
        try:
            self.config.load()
        except Exception as error:
            logger.exception("Preventing restart because of a configuration error:")
            send_notification("Configuration error", str(error.__context__))
            return

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

    def dump_state(self, buf: Any) -> None:
        try:
            pickle.dump(QtileState(self), buf, protocol=0)
        except:  # noqa: E722
            logger.exception("Unable to pickle qtile state")

    @expose_command()
    def reload_config(self) -> None:
        """
        Reload the configuration file.

        Can also be triggered by sending Qtile a SIGUSR1 signal.
        """
        logger.debug("Reloading the configuration file")

        try:
            self.config.load()
        except Exception as error:
            logger.exception("Configuration error:")
            send_notification("Configuration error", str(error))
            return

        self._state = QtileState(self, restart=False)
        self._finalize_configurables()
        hook.clear()
        self.ungrab_keys()
        self.chord_stack.clear()
        self.core.ungrab_buttons()
        self._mouse_map.clear()
        self.groups_map.clear()
        self.groups.clear()
        self.screens.clear()
        remove_dbus_rules()
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
        remove_dbus_rules()
        inhibitor.stop()
        cancel_tasks()
        self.core.finalize()

    def add_autogen_group(self, screen_idx: int) -> _Group:
        name = f"autogen_{screen_idx + 1}"
        self.add_group(name)
        logger.warning("Too few groups in config. Added group: %s", name)
        return self.groups_map[name]

    def get_available_group(self, screen_idx: int) -> _Group | None:
        for group in self.groups:
            # Groups belonging to a screen or a scratchpad are not 'available'
            # to be assigned to a screen
            if group.screen or isinstance(group, ScratchPad):
                continue

            # Only return groups that can be tied to this screen
            # And thus do not have a "screen affinity" explicitly set for another screen
            if group.screen_affinity is None or group.screen_affinity == screen_idx:
                return group
        return None

    def _process_screens(self, reloading: bool = False) -> None:
        current_groups = [s.group for s in self.screens]
        screens = []

        if hasattr(self.config, "fake_screens"):
            screen_info = [
                ScreenRect(s.x, s.y, s.width, s.height) for s in self.config.fake_screens
            ]
            config = self.config.fake_screens
        else:
            # Alias screens with the same x and y coordinates, taking largest
            xywh = {}  # type: dict[tuple[int, int], tuple[int, int]]
            for info in self.core.get_screen_info():
                pos = (info.x, info.y)
                width, height = xywh.get(pos, (0, 0))
                xywh[pos] = (max(width, info.width), max(height, info.height))

            screen_info = [ScreenRect(x, y, w, h) for (x, y), (w, h) in xywh.items()]
            config = self.config.screens

        for i, info in enumerate(screen_info):
            if i + 1 > len(config):
                scr = Screen()
            else:
                scr = config[i]

            if not hasattr(self, "current_screen") or reloading:
                self.current_screen = scr
                reloading = False

            grp = None
            if i < len(current_groups):
                grp = current_groups[i]
            else:
                # We need to assign a new group
                # Get an available group or create a new one
                grp = self.get_available_group(i)
                if grp is None:
                    grp = self.add_autogen_group(i)

            # If the screen has changed position and/or size, or is a new screen then make sure that any gaps/bars
            # are reconfigured
            reconfigure_gaps = (
                (info.x, info.y, info.width, info.height) != (scr.x, scr.y, scr.width, scr.height)
            ) or (i + 1 > len(self.screens))

            if not hasattr(scr, "group"):
                # Ensure that this screen actually *has* a group, as it won't get
                # assigned one during `__init__` because they are created in the config,
                # where the groups also are. This lets us type `Screen.group` as
                # `_Group` rather than `_Group | None` which would need lots of other
                # changes to check for `None`s, and conceptually all screens should have
                # a group anyway.
                scr.group = grp

            scr._configure(
                self,
                i,
                info.x,
                info.y,
                info.width,
                info.height,
                grp,
                reconfigure_gaps=reconfigure_gaps,
            )
            screens.append(scr)

        for screen in self.screens:
            if screen not in screens:
                for gap in screen.gaps:
                    if isinstance(gap, bar.Bar) and gap.window:
                        gap.finalize()

        self.screens = screens

    @expose_command()
    def reconfigure_screens(self, *_: list[Any], **__: dict[Any, Any]) -> None:
        """
        This can be used to set up screens again during run time. Intended usage is to
        be called when the screen_change hook is fired, responding to changes in
        physical monitor setup by configuring qtile.screens accordingly. The args are
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

    def fill_screen(self, screen: Screen, background: ColorType) -> None:
        self.core.painter.fill(screen, background)

    def process_key_event(self, keysym: int, mask: int) -> tuple[Key | KeyChord | None, bool]:
        key = self.keys_map.get((keysym, mask), None)
        if key is None:
            logger.debug("Ignoring unknown keysym: %s, mask: %s", keysym, mask)
            return (None, False)

        if isinstance(key, KeyChord):
            self.grab_chord(key)
        else:
            # Keep track if we have executed a command
            executed = False
            for cmd in key.commands:
                if cmd.check(self):
                    status, val = self.server.call(
                        (cmd.selectors, cmd.name, cmd.args, cmd.kwargs, False)
                    )
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("KB command error %s: %s", cmd.name, val)
                    executed = True
            if self.chord_stack and (not self.chord_stack[-1].mode or key.key == "Escape"):
                self.ungrab_chord()
            # We never swallow when no commands have been executed,
            # even when key.swallow is set to True
            elif not executed:
                return (key, False)
        # Return whether we have handled the key based on the key's swallow parameter
        return (key, key.swallow)

    def grab_keys(self) -> None:
        """Re-grab all of the keys configured in the key map

        Useful when a keyboard mapping event is received.
        """
        self.core.ungrab_keys()
        keys = self.keys_map.copy()
        self.keys_map.clear()
        for key in keys.values():
            self.grab_key(key)

    def grab_key(self, key: Key | KeyChord) -> None:
        """Grab the given key event"""
        syms = self.core.grab_key(key)
        if syms in self.keys_map:
            if self.keys_map[syms] == key:
                # We've already bound this key definition
                return
            logger.warning("Key spec duplicated, overriding previous: %s", key)
        self.keys_map[syms] = key

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
            hook.fire("enter_chord", chord.name)

        self.ungrab_keys()
        for key in chord.submappings:
            self.grab_key(key)

    @expose_command()
    def ungrab_chord(self) -> None:
        """Leave a chord mode"""
        hook.fire("leave_chord")

        self.ungrab_keys()
        if not self.chord_stack:
            logger.debug("ungrab_chord was called when no chord mode was active")
            return
        # The first pop is necessary: Otherwise we would be stuck in a mode;
        # we could not leave it: the code below would re-enter the old mode.
        self.chord_stack.pop()
        # Find another named mode or load the root keybindings:
        while self.chord_stack:
            chord = self.chord_stack.pop()
            if chord.mode:
                self.grab_chord(chord)
                break
        else:
            for key in self.config.keys:
                self.grab_key(key)

    @expose_command()
    def ungrab_all_chords(self) -> None:
        """Leave all chord modes and grab the root bindings"""
        hook.fire("leave_chord")
        self.ungrab_keys()
        self.chord_stack.clear()
        for key in self.config.keys:
            self.grab_key(key)

    def grab_button(self, button: Mouse) -> None:
        """Grab the given mouse button event"""
        try:
            button.modmask = self.core.grab_button(button)
        except utils.QtileError:
            logger.warning("Unknown modifier(s): %s", button.modifiers)
            return
        self._mouse_map[button.button_code].append(button)

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
        index: int | None = None,
        screen_affinity: int | None = None,
        persist: bool | None = False,
    ) -> bool:
        if name not in self.groups_map.keys():
            g = _Group(
                name, layout, label=label, screen_affinity=screen_affinity, persist=persist
            )
            if index is None:
                self.groups.append(g)
            else:
                self.groups.insert(index, g)

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

            # Find a group that's not currently on a screen to bring to the front.
            target = group.get_previous_group(skip_managed=True)

            # move windows to other group
            for i in list(group.windows):
                i.togroup(target.name)

            # if group to be deleted is currently active
            if self.current_group.name == name:
                # switch to target group
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

        The requested space is added to space reserved previously: repeated calls to
        this method are not idempotent.
        """
        for i, pos in enumerate(["left", "right", "top", "bottom"]):
            if space := reserved_space[i]:
                if gap := getattr(screen, pos):
                    gap.adjust_reserved_space(space)
                elif 0 < space:
                    gap = bar.Gap(0)
                    gap.screen = screen
                    setattr(screen, pos, gap)
                    gap.adjust_reserved_space(space)
        screen.resize()

    def free_reserved_space(
        self,
        reserved_space: tuple[int, int, int, int],  # [left, right, top, bottom]
        screen: Screen,
    ) -> None:
        """
        Free up space that has previously been reserved at the edge(s) of a screen.
        """
        # mypy can't work out that the new tuple is also length 4 (see mypy #7509)
        reserved_space = tuple(-i for i in reserved_space)  # type: ignore
        self.reserve_space(reserved_space, screen)

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

        hook.fire("client_managed", win)

    def unmanage(self, wid: int) -> None:
        c = self.windows_map.get(wid)
        if c:
            group = None
            if isinstance(c, base.Static):
                if c.reserved_space:
                    self.free_reserved_space(c.reserved_space, c.screen)
            elif isinstance(c, base.Window):
                if c.group:
                    group = c.group
                    c.group.remove(c)
            del self.windows_map[wid]

            if isinstance(c, base.Window):
                # Put the group back on the window so hooked functions can access it.
                c.group = group
            hook.fire("client_killed", c)

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

    def _focus_hovered_window(self) -> None:
        window = self.core.hovered_window
        if window:
            if isinstance(window, base.Window):
                window.focus()

    def process_button_click(self, button_code: int, modmask: int, x: int, y: int) -> bool:
        handled = False
        for m in self._mouse_map[button_code]:
            if not m.modmask == modmask:
                continue

            if isinstance(m, Click):
                if self.config.follow_mouse_focus == "click_or_drag_only":
                    self._focus_hovered_window()
                for i in m.commands:
                    if i.check(self):
                        status, val = self.server.call(
                            (i.selectors, i.name, i.args, i.kwargs, False)
                        )
                        if status in (interface.ERROR, interface.EXCEPTION):
                            logger.error("Mouse command error %s: %s", i.name, val)
                        handled = True
            elif (
                isinstance(m, Drag) and self.current_window and not self.current_window.fullscreen
            ):
                if self.config.follow_mouse_focus == "click_or_drag_only":
                    self._focus_hovered_window()
                if m.start:
                    i = m.start
                    status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs, False))
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("Mouse command error %s: %s", i.name, val)
                        continue
                else:
                    val = (0, 0)

                if m.warp_pointer and self.current_window is not None:
                    win_size = self.current_window.get_size()
                    win_pos = self.current_window.get_position()
                    x = win_size[0] + win_pos[0]
                    y = win_size[1] + win_pos[1]
                    self.core.warp_pointer(x, y)

                self._drag = (x, y, val[0], val[1], m.commands)
                self.core.grab_pointer()
                handled = True

        return handled

    def process_button_release(self, button_code: int, modmask: int) -> bool:
        if self._drag is not None:
            for m in self._mouse_map[button_code]:
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
                        (i.selectors, i.name, i.args + (rx + dx, ry + dy), i.kwargs, False)
                    )
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("Mouse command error %s: %s", i.name, val)

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
            return False, [x.position for x in self.current_screen.gaps if isinstance(x, bar.Bar)]
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
                return lget(self.current_group.layouts, int(sel))
        elif name == "widget":
            return self.widgets_map.get(sel)  # type: ignore
        elif name == "bar":
            gap = getattr(self.current_screen, sel)  # type: ignore
            if isinstance(gap, bar.Bar):
                return gap
        elif name == "window":
            if sel is None:
                return self.current_window
            else:
                windows: dict[str | int, base.WindowType]
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
                return lget(self.screens, int(sel))
        elif name == "core":
            return self.core
        return None

    def call_soon(self, func: Callable, *args: Any) -> asyncio.Handle:
        """A wrapper for the event loop's call_soon which also flushes the core's
        event queue after func is called."""

        def f() -> None:
            func(*args)
            self.core.flush()

        return self._eventloop.call_soon(f)

    def call_soon_threadsafe(self, func: Callable, *args: Any) -> asyncio.Handle:
        """Another event loop proxy, see `call_soon`."""

        def f() -> None:
            func(*args)
            self.core.flush()

        return self._eventloop.call_soon_threadsafe(f)

    def call_later(self, delay: int | float, func: Callable, *args: Any) -> asyncio.TimerHandle:
        """Another event loop proxy, see `call_soon`."""

        def f() -> None:
            func(*args)
            self.core.flush()

        return self._eventloop.call_later(delay, f)

    def run_in_executor(self, func: Callable, *args: Any) -> asyncio.Future:
        """A wrapper for running a function in the event loop's default
        executor."""
        return self._eventloop.run_in_executor(None, func, *args)

    @expose_command()
    def debug(self) -> None:
        """Set log level to DEBUG"""
        logger.setLevel(logging.DEBUG)
        logger.debug("Switching to DEBUG threshold")

    @expose_command()
    def info(self) -> None:
        """Set log level to INFO"""
        logger.setLevel(logging.INFO)
        logger.info("Switching to INFO threshold")

    @expose_command()
    def warning(self) -> None:
        """Set log level to WARNING"""
        logger.setLevel(logging.WARNING)
        logger.warning("Switching to WARNING threshold")

    @expose_command()
    def error(self) -> None:
        """Set log level to ERROR"""
        logger.setLevel(logging.ERROR)
        logger.error("Switching to ERROR threshold")

    @expose_command()
    def critical(self) -> None:
        """Set log level to CRITICAL"""
        logger.setLevel(logging.CRITICAL)
        logger.critical("Switching to CRITICAL threshold")

    @expose_command()
    def loglevel(self) -> int:
        return logger.level

    @expose_command()
    def loglevelname(self) -> str:
        return logging.getLevelName(logger.level)

    @expose_command()
    def pause(self) -> None:
        """Drops into pdb"""
        import pdb

        pdb.set_trace()

    @expose_command()
    def get_groups(self) -> dict[str, dict[str, Any]]:
        """
        Return a dictionary containing information for all groups

        Examples
        ========

            get_groups()
        """
        return {i.name: i.info() for i in self.groups}

    @expose_command()
    def display_kb(self) -> str:
        """Display table of key bindings"""

        class FormatTable:
            def __init__(self) -> None:
                self.max_col_size: list[int] = []
                self.rows: list[list[str]] = []

            def add(self, row: list[str]) -> None:
                n = len(row) - len(self.max_col_size)
                if n > 0:
                    self.max_col_size += [0] * n
                for i, f in enumerate(row):
                    if len(f) > self.max_col_size[i]:
                        self.max_col_size[i] = len(f)
                self.rows.append(row)

            def getformat(self) -> tuple[str, int]:
                format_string = " ".join(
                    f"%-{max_col_size + 2:d}s" for max_col_size in self.max_col_size
                )
                return format_string + "\n", len(self.max_col_size)

            def expandlist(self, list_: list[str], n: int) -> list[str]:
                if not list_:
                    return ["-" * max_col_size for max_col_size in self.max_col_size]
                n -= len(list_)
                if n > 0:
                    list_ += [""] * n
                return list_

            def __str__(self) -> str:
                format_, n = self.getformat()
                return "".join(format_ % tuple(self.expandlist(row, n)) for row in self.rows)

        result = FormatTable()
        result.add(["Mode", "KeySym", "Mod", "Command", "Desc"])
        result.add([])
        rows = []

        def walk_binding(k: Key | KeyChord, mode: str) -> None:
            nonlocal rows
            modifiers = ", ".join(k.modifiers)
            if isinstance(k.key, int):
                name = hex(k.key)
            else:
                name = k.key

            if isinstance(k, Key):
                if not k.commands:
                    return
                allargs = ", ".join(
                    [
                        value.__name__ if callable(value) else repr(value)
                        for value in k.commands[0].args
                    ]
                    + [
                        f"{keyword} = {repr(value)}"
                        for keyword, value in k.commands[0].kwargs.items()
                    ]
                )
                rows.append(
                    [
                        mode,
                        name,
                        modifiers,
                        f"{k.commands[0].name:s}({allargs:s})",
                        k.desc,
                    ]
                )
                return
            if isinstance(k, KeyChord):
                new_mode_s = k.name if k.name else "<unnamed>"
                new_mode = (
                    k.name
                    if mode == "<root>"
                    else "{}>{}".format(mode, k.name if k.name else "_")
                )
                rows.append([mode, name, modifiers, "", f"Enter {new_mode_s:s} mode"])
                for s in k.submappings:
                    walk_binding(s, new_mode)
                return
            raise TypeError(f"Unexpected type: {type(k)}")

        for k in self.config.keys:
            walk_binding(k, "<root>")
        rows.sort()
        for row in rows:
            result.add(row)
        return str(result)

    @expose_command()
    def list_widgets(self) -> list[str]:
        """List of all addressible widget names"""
        return list(self.widgets_map.keys())

    @expose_command()
    def to_layout_index(self, index: int, name: str | None = None) -> None:
        """
        Switch to the layout with the given index in self.layouts.

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

    @expose_command()
    def next_layout(self, name: str | None = None) -> None:
        """
        Switch to the next layout.

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

    @expose_command()
    def prev_layout(self, name: str | None = None) -> None:
        """
        Switch to the previous layout.

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

    @expose_command()
    def get_screens(self) -> list[dict[str, Any]]:
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

    @expose_command()
    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        """Simulates a keypress on the focused window.

        This triggers internal bindings only; for full simulation see external tools
        such as xdotool or ydotool.

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

    @expose_command()
    def validate_config(self) -> None:
        try:
            self.config.load()
        except Exception as error:
            send_notification("Configuration check", str(error))
        else:
            send_notification("Configuration check", "No error found!")

    @expose_command()
    def spawn(
        self, cmd: list[str] | str, shell: bool = False, env: dict[str, str] = dict()
    ) -> int:
        """
        Spawn a new process.

        Parameters
        ==========
        cmd:
            The command to execute either as a single string or list of strings.
        shell:
            Whether to execute the command in a new shell by prepending it with "/bin/sh
            -c". This enables the use of shell syntax within the command (e.g. pipes).
        env:
            Dictionary of environmental variables to pass with command.

        Examples
        ========

            spawn("firefox")

            spawn(["xterm", "-T", "Temporary terminal"])

            spawn("screenshot | xclip", shell=True)
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
            logger.error("couldn't find `%s`", to_lookup)
            return -1

        if len(env) == 0:
            env = os.environ.copy()
            # if qtile was installed in a virutal env, we don't
            # necessarily want to propagate that to children
            # applications, since it may change e.g. the behavior
            # of shells that spawn python applications
            env.pop("VIRTUAL_ENV", None)

        # std{in,out,err} should be /dev/null
        null = os.open("/dev/null", os.O_RDONLY)
        file_actions: list[tuple] = [
            (os.POSIX_SPAWN_DUP2, 0, null),
            (os.POSIX_SPAWN_DUP2, 1, null),
            (os.POSIX_SPAWN_DUP2, 2, null),
        ]

        if sys.version_info.major >= 3 and sys.version_info.minor >= 13:
            # we should close all fds so that child processes don't
            # accidentally write to our x11 event loop or whatever; we never
            # used to do this, so it seems fine to only do it on python 3.13 or
            # above, where this nice API to do it exists.
            file_actions.append((os.POSIX_SPAWN_CLOSEFROM, 3))  # type: ignore

        try:
            return os.posix_spawnp(args[0], args, env, file_actions=file_actions)
        except OSError as e:
            logger.warning("failed to execute: %s: %s", str(args), str(e))
            return -1

    @expose_command()
    def status(self) -> Literal["OK"]:
        """Return "OK" if Qtile is running"""
        return "OK"

    @expose_command()
    def sync(self) -> None:
        """
        Sync the backend's event queue. Should only be used for development.
        """
        self.core.flush()

    @expose_command()
    def to_screen(self, n: int) -> None:
        """Warp focus to screen n, where n is a 0-based screen number

        Examples
        ========

            to_screen(0)
        """
        self.focus_screen(n)

    @expose_command()
    def next_screen(self) -> None:
        """Move to next screen"""
        self.focus_screen((self.screens.index(self.current_screen) + 1) % len(self.screens))

    @expose_command()
    def prev_screen(self) -> None:
        """Move to the previous screen"""
        self.focus_screen((self.screens.index(self.current_screen) - 1) % len(self.screens))

    @expose_command()
    def windows(self) -> list[dict[str, Any]]:
        """Return info for each client window"""
        return [
            i.info()
            for i in self.windows_map.values()
            if not isinstance(i, base.Internal | _Widget) and isinstance(i, CommandObject)
        ]

    @expose_command()
    def internal_windows(self) -> list[dict[str, Any]]:
        """Return info for each internal window (bars, for example)"""
        return [i.info() for i in self.windows_map.values() if isinstance(i, base.Internal)]

    @expose_command()
    def qtile_info(self) -> dict:
        """Returns a dictionary of info on the Qtile instance"""
        config_path = self.config.file_path
        dictionary = {
            "version": VERSION,
            "log_level": self.loglevelname(),
        }

        if isinstance(logger.handlers[0], RotatingFileHandler):
            log_path = logger.handlers[0].baseFilename
            dictionary["log_path"] = log_path

        if isinstance(config_path, str):
            dictionary["config_path"] = config_path
        elif isinstance(config_path, Path):
            dictionary["config_path"] = config_path.as_posix()

        return dictionary

    @expose_command()
    def shutdown(self, exitcode: int = 0) -> None:
        """Quit Qtile

        Parameters
        ==========
        exitcode :
            Set exit status of Qtile. Can be e.g. used to make login managers
            poweroff or restart the system. (default: 0)
        """
        self.stop(exitcode)

    @expose_command()
    def switch_groups(self, namea: str, nameb: str) -> None:
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

    @expose_command()
    def findwindow(self, prompt: str = "window", widget: str = "prompt") -> None:
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
            logger.error("No widget named '%s' present.", widget)
            return

        mb.start_input(prompt, self.find_window, "window", strict_completer=True)

    @expose_command()
    def switch_window(self, location: int) -> None:
        """
        Change to the window at the specified index in the current group.
        """
        windows = self.current_group.windows
        if location < 1 or location > len(windows):
            return

        self.current_group.focus(windows[location - 1])

    @expose_command()
    def change_window_order(self, new_location: int) -> None:
        """
        Change the order of the current window within the current group.
        """
        if new_location < 1 or new_location > len(self.current_group.windows):
            return

        windows = self.current_group.windows
        current_window_index = windows.index(self.current_window)

        temp = windows[current_window_index]
        windows[current_window_index] = windows[new_location - 1]
        windows[new_location - 1] = temp

    @expose_command()
    def next_urgent(self) -> None:
        """Focus next window with urgent hint"""
        try:
            nxt = [w for w in self.windows_map.values() if w.urgent][0]
            assert isinstance(nxt, base.Window)
            if nxt.group:
                nxt.group.toscreen()
                nxt.group.focus(nxt)
            else:
                self.current_screen.group.add(nxt)
                self.current_screen.group.focus(nxt)
        except IndexError:
            pass  # no window had urgent set

    @expose_command()
    def togroup(self, prompt: str = "group", widget: str = "prompt") -> None:
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
            logger.error("No widget named '%s' present.", widget)
            return

        mb.start_input(prompt, self.move_to_group, "group", strict_completer=True)

    @expose_command()
    def switchgroup(self, prompt: str = "group", widget: str = "prompt") -> None:
        """Launch prompt widget to switch to a given group to the current screen

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "group")
        widget :
            Name of the prompt widget (default: "prompt")
        """

        def f(group: str) -> None:
            if group:
                try:
                    self.groups_map[group].toscreen()
                except KeyError:
                    logger.warning("No group named '%s' present.", group)

        mb = self.widgets_map.get(widget)
        if not mb:
            logger.error("No widget named '%s' present.", widget)
            return

        mb.start_input(prompt, f, "group", strict_completer=True)

    @expose_command()
    def labelgroup(self, prompt: str = "label", widget: str = "prompt") -> None:
        """Launch prompt widget to label the current group

        Parameters
        ==========
        prompt :
            Text with which to prompt user (default: "label")
        widget :
            Name of the prompt widget (default: "prompt")
        """

        def f(name: str) -> None:
            self.current_group.set_label(name or None)

        try:
            mb = self.widgets_map[widget]
            mb.start_input(prompt, f, allow_empty_input=True)
        except KeyError:
            logger.error("No widget named '%s' present.", widget)

    @expose_command()
    def spawncmd(
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

        def f(args: str) -> None:
            if args:
                if aliases and args in aliases:
                    args = aliases[args]
                self.spawn(command % args, shell=shell)

        try:
            mb = self.widgets_map[widget]
            mb.start_input(prompt, f, complete, aliases=aliases)
        except KeyError:
            logger.error("No widget named '%s' present.", widget)

    @expose_command()
    def qtilecmd(
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

        def f(cmd: str) -> None:
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
                    result = eval(f"c.{cmd:s}")
                except (CommandError, CommandException, AttributeError):
                    logger.exception("Command errored:")
                    result = None
                if result is not None:
                    from pprint import pformat

                    message = pformat(result)
                    if messenger:
                        self.spawn(f'{messenger:s} "{message:s}"')
                    logger.debug(result)

        mb = self.widgets_map[widget]
        if not mb:
            logger.error("No widget named %s present.", widget)
            return
        mb.start_input(prompt, f, "qshell")

    @expose_command()
    def addgroup(
        self,
        group: str,
        label: str | None = None,
        layout: str | None = None,
        layouts: list[Layout] | None = None,
        index: int | None = None,
        persist: bool | None = False,
    ) -> bool:
        """Add a group with the given name"""
        return self.add_group(
            name=group, layout=layout, layouts=layouts, label=label, index=index, persist=persist
        )

    @expose_command()
    def delgroup(self, group: str) -> None:
        """Delete a group with the given name"""
        self.delete_group(group)

    @expose_command()
    def add_rule(
        self,
        match_args: dict[str, Any],
        rule_args: dict[str, Any],
        min_priorty: bool = False,
    ) -> int | None:
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
            return None

        match = Match(**match_args)
        rule = Rule([match], **rule_args)
        return self.dgroups.add_rule(rule, min_priorty)

    @expose_command()
    def remove_rule(self, rule_id: int) -> None:
        """Remove a dgroup rule by rule_id"""
        self.dgroups.remove_rule(rule_id)

    @expose_command()
    def hide_show_bar(
        self,
        position: Literal["top", "bottom", "left", "right", "all"] = "all",
        screen: Literal["current", "all"] = "current",
    ) -> None:
        """Toggle visibility of a given bar

        Parameters
        ==========
        position :
            one of: "top", "bottom", "left", "right", or "all" (default: "all")
        screen :
            one of: "current", "all" (default: "current")
        """
        to_mod = [self.current_screen]
        if screen == "all":
            to_mod = self.screens
        for s in to_mod:
            self.hide_show_bar_screen(s, position)

    def hide_show_bar_screen(
        self,
        screen: Screen,
        position: Literal["top", "bottom", "left", "right", "all"] = "all",
    ) -> None:
        if position in ["top", "bottom", "left", "right"]:
            bar = getattr(screen, position)
            if bar:
                bar.show(not bar.is_show())
                self.current_group.layout_all()
            else:
                logger.warning("Not found bar in position '%s' for hide/show.", position)
        elif position == "all":
            is_show = None
            for bar in [screen.left, screen.right, screen.top, screen.bottom]:
                if isinstance(bar, libqtile.bar.Bar):
                    if is_show is None:
                        is_show = not bar.is_show()
                    bar.show(is_show)
            if is_show is not None:
                self.current_group.layout_all()
            else:
                logger.warning("Not found bar for hide/show.")
        else:
            logger.warning("Invalid position value:%s", position)

    @expose_command()
    def get_state(self) -> str:
        """Get pickled state for restarting qtile"""
        buf = io.BytesIO()
        self.dump_state(buf)
        state = buf.getvalue().decode(errors="backslashreplace")
        logger.debug("State = %s", state)
        return state

    @expose_command()
    def tracemalloc_toggle(self) -> None:
        """Toggle tracemalloc status

        Running tracemalloc is required for `qtile top`
        """
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        else:
            tracemalloc.stop()

    @expose_command()
    def tracemalloc_dump(self) -> tuple[bool, str]:
        """Dump tracemalloc snapshot"""
        import tracemalloc

        if not tracemalloc.is_tracing():
            return False, "Trace not started"
        cache_directory = get_cache_dir()
        malloc_dump = os.path.join(cache_directory, "qtile_tracemalloc.dump")
        tracemalloc.take_snapshot().dump(malloc_dump)
        return True, malloc_dump

    @expose_command()
    def get_test_data(self) -> Any:
        """
        Returns any content arbitrarily set in the self.test_data attribute.
        Useful in tests.
        """
        return self.test_data

    @expose_command()
    def run_extension(self, extension: _Extension) -> None:
        """Run extensions"""
        extension.run()

    @expose_command()
    def fire_user_hook(self, hook_name: str, *args: Any) -> None:
        """Fire a custom hook."""
        hook.fire(f"user_{hook_name}", *args)
