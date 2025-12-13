# Copyright (c) 2018 Sean Vig
#
# This file contains code copied or adapted from pywlroots,
# which is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# - Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimers.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimers in the documentation
#   and/or other materials provided with the distribution.
#
# - Neither the names of the developers nor the names of its contributors may be
#   used to endorse or promote products derived from this Software without
#   specific prior written permission.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Modifications Copyright (c) 2025 The Qtile Project
#
# Licensed under the MIT License.
# See the LICENSE file in the root of this repository for details.

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import operator
import os
import signal
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.wayland import inputs
from libqtile.backend.wayland.idle_inhibit import InhibitorManager
from libqtile.backend.wayland.window import Internal, Static, Window
from libqtile.command.base import allow_when_locked, expose_command
from libqtile.config import ScreenRect
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.utils import QtileError, reap_zombies, rgb

try:
    from libqtile.backend.wayland._ffi import ffi, lib

except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")

    from libqtile.backend.wayland.ffi_stub import ffi, lib

if TYPE_CHECKING:
    from libqtile import config
    from libqtile.config import Screen
    from libqtile.utils import ColorType


def translate_masks(modifiers: list[str]) -> int:
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    assert ffi is not None
    assert lib is not None
    for i in modifiers:
        code = int(lib.qw_util_get_modifier_code(i.lower().encode()))
        if code == -1:
            raise QtileError(f"unknown modifier: {i}")
        masks.append(code)
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


@ffi.def_extern()
def log_cb(importance: int, formatted_str: ffi.CData) -> None:
    """Callback that logs the string at the given level"""
    log_str = ffi.string(formatted_str).decode()
    if importance == lib.WLR_ERROR:
        logger.error(log_str)
    elif importance == lib.WLR_INFO:
        logger.info(log_str)
    elif importance == lib.WLR_DEBUG:
        logger.debug(log_str)


@ffi.def_extern()
def keyboard_key_cb(keysym: int, mask: int, userdata: ffi.CData) -> int:
    core = ffi.from_handle(userdata)
    if core.handle_keyboard_key(keysym, mask):
        return 1
    return 0


@ffi.def_extern()
def manage_view_cb(view: ffi.CData, userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_manage_view(view)


@ffi.def_extern()
def unmanage_view_cb(view: ffi.CData, userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_unmanage_view(view)


@ffi.def_extern()
def cursor_motion_cb(userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_cursor_motion()


@ffi.def_extern()
def cursor_button_cb(
    button: int, mask: int, pressed: bool, x: int, y: int, userdata: ffi.CData
) -> int:
    core = ffi.from_handle(userdata)
    if core.handle_cursor_button(button, mask, pressed, x, y):
        return 1
    return 0


@ffi.def_extern()
def on_screen_change_cb(userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_screen_change()


@ffi.def_extern()
def on_screen_reserve_space_cb(output: ffi.CData, userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_screen_reserve_space(output)


@ffi.def_extern()
def view_activation_cb(view: ffi.CData, userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_view_activation(view)


@ffi.def_extern()
def on_input_device_added_cb(userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.handle_input_device_added()


@ffi.def_extern()
def focus_current_window_cb(userdata: ffi.CData) -> bool:
    core = ffi.from_handle(userdata)
    return core.handle_focus_current_window()


@ffi.def_extern()
def on_session_lock_cb(locked: bool, userdata: ffi.CData) -> None:
    core = ffi.from_handle(userdata)
    core.set_locked(locked)


@ffi.def_extern()
def get_current_output_dims_cb(userdata: ffi.CData) -> ffi.CData:
    core = ffi.from_handle(userdata)
    return core.handle_get_current_output_dims()


@ffi.def_extern()
def add_idle_inhibitor_cb(
    userdata: ffi.CData,
    inhibitor: ffi.CData,
    view: ffi.CData,
    is_layer_surface: bool,
    is_session_lock_surface: bool,
) -> bool:
    core = ffi.from_handle(userdata)
    if view != ffi.NULL:
        window = ffi.from_handle(view)
    else:
        window = None
    return core.handle_new_idle_inhibitor(
        inhibitor, window, is_layer_surface, is_session_lock_surface
    )


@ffi.def_extern()
def remove_idle_inhibitor_cb(userdata: ffi.CData, inhibitor: ffi.CData) -> bool:
    core = ffi.from_handle(userdata)
    return core.handle_remove_idle_inhibitor(inhibitor)


@ffi.def_extern()
def check_inhibited_cb(userdata: ffi.CData) -> bool:
    core = ffi.from_handle(userdata)
    return core.check_inhibited()


def get_wlr_log_level() -> int:
    if logger.level <= logging.DEBUG:
        return lib.WLR_DEBUG
    elif logger.level <= logging.INFO:
        return lib.WLR_INFO
    elif logger.level <= logging.ERROR:
        return lib.WLR_ERROR
    return lib.WLR_SILENT


class Core(base.Core):
    supports_restarting: bool = False

    def __init__(self) -> None:
        # this Internal window receives keyboard input, e.g. via the Prompt widget.
        self.focused_internal: base.Internal | None = None

        """Setup the Wayland core backend"""
        lib.qw_log_init(get_wlr_log_level(), lib.log_cb)
        self.qw = lib.qw_server_create()
        if not self.qw:
            sys.exit(1)

        xwayland_display_name_ptr = lib.qw_server_xwayland_display_name(self.qw)
        if xwayland_display_name_ptr != ffi.NULL:
            os.environ["DISPLAY"] = ffi.string(xwayland_display_name_ptr).decode()
        self._output_reserved_space: dict[Screen, tuple[int, int, int, int]] = {}
        self.current_window = None
        self.grabbed_keys: list[tuple[int, int]] = []
        self._userdata = ffi.new_handle(self)
        self.qw.cb_data = self._userdata
        self.qw.keyboard_key_cb = lib.keyboard_key_cb
        self.qw.manage_view_cb = lib.manage_view_cb
        self.qw.unmanage_view_cb = lib.unmanage_view_cb
        self.qw.cursor_motion_cb = lib.cursor_motion_cb
        self.qw.cursor_button_cb = lib.cursor_button_cb
        self.qw.on_screen_change_cb = lib.on_screen_change_cb
        self.qw.on_screen_reserve_space_cb = lib.on_screen_reserve_space_cb
        self.qw.view_activation_cb = lib.view_activation_cb
        self.qw.view_activation_cb_data = self._userdata
        self.qw.on_input_device_added_cb = lib.on_input_device_added_cb
        self.qw.focus_current_window_cb = lib.focus_current_window_cb
        self.qw.on_session_lock_cb = lib.on_session_lock_cb
        self.qw.get_current_output_dims_cb = lib.get_current_output_dims_cb
        self.qw.add_idle_inhibitor_cb = lib.add_idle_inhibitor_cb
        self.qw.remove_idle_inhibitor_cb = lib.remove_idle_inhibitor_cb
        self.qw.check_inhibited_cb = lib.check_inhibited_cb
        lib.qw_server_start(self.qw)
        os.environ["WAYLAND_DISPLAY"] = self.display_name
        self.qw_cursor = lib.qw_server_get_cursor(self.qw)

        self.painter = Painter(self)
        self._locked = False
        self.inhibitor_manager = InhibitorManager(self)
        self._inhibited = False

    def update_backend_log_level(self) -> None:
        """Update the wlr log level based on Qtile's log level."""
        lib.qw_log_init(get_wlr_log_level(), lib.log_cb)

    def clear_focus(self) -> None:
        """Clear TODO so that there is no focused window"""
        # TODO

    def new_wid(self) -> int:
        """Get a new unique window ID"""
        assert self.qtile is not None
        return max(self.qtile.windows_map.keys(), default=0) + 1

    def on_config_load(self, initial: bool) -> None:
        assert self.qtile is not None

        # Apply input device configuration
        if self.qtile.config.wl_input_rules:
            inputs.configure_input_devices(self.qw, self.qtile.config.wl_input_rules)

        if initial:
            # This backend does not support restarting
            return

        managed_wins = [w for w in self.qtile.windows_map.values() if isinstance(w, Window)]
        for win in managed_wins:
            group = None
            if win.group:
                if win.group.name in self.qtile.groups_map:
                    # Put window on group with same name as its old group if one exists
                    group = self.qtile.groups_map[win.group.name]
                else:
                    # Otherwise place it on the group at the same index
                    for i, old_group in self.qtile._state.groups:  # type: ignore
                        if i < len(self.qtile.groups):
                            name = old_group[0]
                            if win.group.name == name:
                                group = self.qtile.groups[i]
                if win in win.group.windows:
                    # Remove window from old group
                    win.group.remove(win)
            if group is None:
                # Falling back to current group if none found
                group = self.qtile.current_group
            group.add(win)
            if group == self.qtile.current_group:
                win.unhide()
            else:
                win.hide()

    def handle_input_device_added(self) -> None:
        if not hasattr(self, "qtile"):
            return
        if self.qtile.config.wl_input_rules:
            inputs.configure_input_devices(self.qw, self.qtile.config.wl_input_rules)

        # TODO: Also configure devices when a new device is added

    def handle_screen_change(self) -> None:
        hook.fire("screen_change", None)

    def get_screen_for_output(self, output: ffi.CData) -> Screen:
        assert self.qtile is not None

        for screen in self.qtile.screens:
            # Outputs alias if they have the same (x, y) and share the same Screen, so
            # we don't need to check the if the width and height match the Screen's.
            if screen.x == output.x and screen.y == output.y:
                return screen

        return self.qtile.current_screen

    def handle_get_current_output_dims(self) -> ffi.CData:
        assert self.qtile is not None

        output_dims = ffi.new("struct wlr_box *")
        output_dims.x = self.qtile.current_screen.x
        output_dims.y = self.qtile.current_screen.y
        output_dims.width = self.qtile.current_screen.width
        output_dims.height = self.qtile.current_screen.height

        # Dereference to pass by value
        return output_dims[0]

    def handle_screen_reserve_space(self, output: ffi.CData) -> None:
        screen = self.get_screen_for_output(output)
        # TODO: is full_area correct here?
        # the old backend used ow and oh
        new_reserved_space = (
            output.area.x - output.x,  # left
            output.x + output.full_area.width - output.area.x - output.area.width,  # right
            output.area.y - output.y,  # top
            output.y + output.full_area.height - output.area.y - output.area.height,  # bottom
        )

        old_reserved = self._output_reserved_space.get(screen, (0, 0, 0, 0))
        delta = tuple(new - old for new, old in zip(new_reserved_space, old_reserved))
        # TODO: this is always True now I think, maybe remove the if?
        if any(delta):
            self.qtile.reserve_space(delta, screen)
            self._output_reserved_space[screen] = new_reserved_space

    def handle_cursor_motion(self) -> None:
        assert self.qtile is not None
        self._focus_pointer(motion=True)
        self.qtile.process_button_motion(
            int(self.qw_cursor.cursor.x), int(self.qw_cursor.cursor.y)
        )

    def handle_cursor_button(self, button: int, mask: int, pressed: bool, x: int, y: int) -> bool:
        assert self.qtile is not None
        if pressed:
            if not self.qw_cursor.implicit_grab.live:
                self._focus_by_click()

            handled = self.qtile.process_button_click(int(button), int(mask), x, y)

            if isinstance(self.qtile.hovered_window, Internal):
                self.qtile.hovered_window.process_button_click(
                    int(self.qw_cursor.cursor.x - self.qtile.hovered_window.x),
                    int(self.qw_cursor.cursor.y - self.qtile.hovered_window.y),
                    int(button),
                )

            return handled
        else:
            return self.qtile.process_button_release(button, mask)

    def handle_manage_view(self, view: ffi.CData) -> None:
        wid = self.new_wid()
        view.wid = wid

        win = Window(self.qtile, view, wid)
        if view.title != ffi.NULL:
            win.name = ffi.string(view.title).decode()
        if view.app_id != ffi.NULL:
            win._wm_class = ffi.string(view.app_id).decode()
        if view.instance != ffi.NULL:
            win._wm_instance = ffi.string(view.instance).decode()
        if view.role != ffi.NULL:
            win._wm_role = ffi.string(view.role).decode()
        win._float_width = win.width  # todo: should we be using getter/setter for _float_width
        win._float_height = win.height

        # Check if any user-defined inhibitor rules match the window
        win.add_config_inhibitors()

        self.qtile.manage(win)
        if win.group and win.group.screen:
            self.check_screen_fullscreen_background(win.group.screen)

    def handle_unmanage_view(self, view: ffi.CData) -> None:
        assert self.qtile is not None
        self.inhibitor_manager.remove_window_inhibitor_by_wid(view.wid)
        self.qtile.unmanage(view.wid)
        self.check_screen_fullscreen_background()

    def handle_keyboard_key(self, keysym: int, mask: int) -> bool:
        if (keysym, mask) in self.grabbed_keys:
            assert self.qtile is not None
            _, swallowed = self.qtile.process_key_event(keysym, mask)
            if swallowed:
                return True

        if self.focused_internal:
            self.focused_internal.process_key_press(keysym)
            return True

        return False

    def handle_focus_current_window(self) -> bool:
        group = self.qtile.current_screen.group
        if group.current_window:
            group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            return True
        else:
            return False

    def focus_window(self, win: base.WindowType) -> None:
        if self.qw.exclusive_layer != ffi.NULL:
            logger.debug("Keyboard focus withheld: focus is fixed to exclusive layer surface.")
            return

        if isinstance(win, base.Internal):
            self.focused_internal = win
            lib.qw_server_keyboard_clear_focus(self.qw)
            return

        if self.focused_internal:
            self.focused_internal = None

        # TODO logic imcomplete
        win._ptr.focus(win._ptr, False)  # What is the second argument?

    def _focus_by_click(self) -> ffi.CData:
        assert self.qtile is not None
        view = self.qw_cursor.view

        if view != ffi.NULL:
            win = self.qtile.windows_map.get(view.wid)

            if win is not None and self.qtile.config.bring_front_click is True:
                win.bring_to_front()
            elif self.qtile.config.bring_front_click == "floating_only":
                if isinstance(win, base.Window) and win.floating:
                    win.bring_to_front()

            if isinstance(win, Static):
                if win.screen is not self.qtile.current_screen:
                    self.qtile.focus_screen(win.screen.index, warp=False)
                win.focus(False)
            elif isinstance(win, base.Window):
                if win.group and win.group.screen is not self.qtile.current_screen:
                    self.qtile.focus_screen(win.group.screen.index, warp=False)
                self.qtile.current_group.focus(win, False)

        else:
            screen = self.qtile.find_screen(
                int(self.qw_cursor.cursor.x), int(self.qw_cursor.cursor.y)
            )
            if screen:
                self.qtile.focus_screen(screen.index, warp=False)

        return view

    def _focus_pointer(self, motion: bool) -> None:
        assert self.qtile is not None
        view = self.qw_cursor.view

        if view == ffi.NULL:
            return

        win = self.qtile.windows_map.get(view.wid)

        if self.qtile.hovered_window is not win:
            # We only want to fire client_mouse_enter once, so check
            # self.qtile.hovered_window.
            hook.fire("client_mouse_enter", win)

        if win is not self.qtile.current_window:
            if motion and self.qtile.config.follow_mouse_focus is True:
                if isinstance(win, Static):
                    self.qtile.focus_screen(win.screen.index, False)
                elif win is not None:
                    if win.group and win.group.current_window != win:
                        win.group.focus(win, False)
                    if (
                        win.group
                        and win.group.screen
                        and self.qtile.current_screen != win.group.screen
                    ):
                        self.qtile.focus_screen(win.group.screen.index, False)

        self.qtile.hovered_window = win

    def handle_view_activation(self, view: ffi.CData) -> None:
        """Handle view urgency notification"""
        assert self.qtile is not None
        wid = view.wid
        win = self.qtile.windows_map.get(wid)

        if win:
            win.activate_by_config()

    def finalize(self) -> None:
        lib.qw_server_finalize(self.qw)

    @property
    def display_name(self) -> str:
        return ffi.string(self.qw.socket).decode()

    def create_internal(self, x: int, y: int, width: int, height: int) -> base.Internal:
        ptr = lib.qw_server_internal_view_new(self.qw, x, y, width, height)
        if not ptr:
            raise RuntimeError("failed creating internal view")
        wid = self.new_wid()
        internal = Internal(self.qtile, ptr, wid)
        self.qtile.manage(internal)
        return internal

    def get_screen_info(self) -> list[ScreenRect]:
        rects = []

        @ffi.callback("void(int, int, int, int)")
        def loop(x: int, y: int, width: int, height: int) -> None:
            rects.append(ScreenRect(x, y, width, height))

        lib.qw_server_loop_output_dims(self.qw, loop)

        return rects

    def _get_sym_from_code(self, keycode: int) -> int:
        sym = lib.qw_server_get_sym_from_code(self.qw, keycode)
        if not sym:
            raise QtileError("Unable to grab keycode. No active keyboard found.")
        return sym

    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        if isinstance(key.key, str):
            keysym = lib.qwu_keysym_from_name(key.key.encode())
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = translate_masks(key.modifiers)
        self.grabbed_keys.append((keysym, mask_key))
        return keysym, mask_key

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        if isinstance(key.key, str):
            keysym = lib.qwu_keysym_from_name(key.key.encode())
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = translate_masks(key.modifiers)
        self.grabbed_keys.remove((keysym, mask_key))
        return keysym, mask_key

    def ungrab_keys(self) -> None:
        self.grabbed_keys.clear()

    def grab_button(self, mouse: config.Mouse) -> int:
        return translate_masks(mouse.modifiers)

    def warp_pointer(self, x: float, y: float) -> None:
        """Warp the pointer to the coordinates in relative to the output layout"""
        lib.qw_cursor_warp_cursor(self.qw_cursor, x, y)

    @contextlib.contextmanager
    def masked(self) -> Generator:
        yield
        # Update pointer focus without cursor motion
        lib.qw_cursor_update_pointer_focus(self.qw_cursor)
        self._focus_pointer(motion=False)

    @property
    def name(self) -> str:
        return "wayland"

    def setup_listener(self) -> None:
        """Setup a listener for the given qtile instance"""
        logger.debug("Adding io watch")
        self.fd = lib.qw_server_get_event_loop_fd(self.qw)
        if self.fd:
            asyncio.get_running_loop().add_reader(self.fd, self._poll)
            asyncio.get_running_loop().add_signal_handler(signal.SIGCHLD, reap_zombies)
        else:
            raise RuntimeError("Failed to get Wayland event loop file descriptor.")

    def remove_listener(self) -> None:
        """Remove the listener from the given event loop"""
        if self.fd is not None:
            logger.debug("Removing io watch")
            loop = asyncio.get_running_loop()
            loop.remove_reader(self.fd)
            self.fd = None

    def _poll(self) -> None:
        lib.qw_server_poll(self.qw)

    def flush(self) -> None:
        self._poll()

    def graceful_shutdown(self) -> None:
        """Try to close windows gracefully before exiting"""
        assert self.qtile is not None

        # Copy in case the dictionary changes during the loop
        for win in self.qtile.windows_map.copy().values():
            win.kill()

        # give everyone a little time to exit and write their state. but don't
        # sleep forever (1s).
        end = time.time() + 1
        while time.time() < end:
            self._poll()
            if not self.qtile.windows_map:
                break

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        return lib.qwu_keysym_from_name(name.encode())

    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        """Simulates a keypress on the focused window."""
        keysym = lib.qwu_keysym_from_name(key.encode())
        mods = translate_masks(modifiers)

        if (keysym, mods) in self.grabbed_keys:
            assert self.qtile is not None
            self.qtile.process_key_event(keysym, mods)
            return

        # Not sure if this is required. process_key_press() appears to be unimplemented in
        # the original wayland backend
        #
        # if self.focused_internal:
        #     self.focused_internal.process_key_press(keysym)

    def set_locked(self, locked: bool) -> None:
        if locked != self._locked:
            if locked:
                hook.fire("locked")
            else:
                hook.fire("unlocked")
        self._locked = locked

    def get_mouse_position(self) -> tuple[int, int]:
        """Get mouse coordinates."""
        return int(self.qw_cursor.cursor.x), int(self.qw_cursor.cursor.y)

    @expose_command()
    def set_keymap(
        self,
        layout: str | None = None,
        options: str | None = None,
        variant: str | None = None,
    ) -> None:
        """
        Set the keymap for the current keyboard.

        The options correspond to xkbcommon configuration environmental variables and if
        not specified are taken from the environment. Acceptable values are strings
        identical to those accepted by the env variables.
        """
        lib.qw_server_set_keymap(
            self.qw,
            ffi.new("char[]", (layout or "").encode()),
            ffi.new("char[]", (options or "").encode()),
            ffi.new("char[]", (variant or "").encode()),
        )

    @expose_command()
    @allow_when_locked
    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal to that specified"""
        success = lib.qw_server_change_vt(self.qw, vt)
        if not success:
            logger.warning("Could not change VT to: %s", vt)
        return success

    @expose_command()
    def hide_cursor(self) -> None:
        """Hide the cursor."""
        lib.qw_cursor_hide(self.qw_cursor)

    @expose_command()
    def unhide_cursor(self) -> None:
        """Unhide the cursor."""
        lib.qw_cursor_show(self.qw_cursor)

    @expose_command()
    def get_inputs(self) -> dict[str, list[dict[str, str]]]:
        """Get information on all input devices."""
        raise Exception("TODO: implement")

    @expose_command()
    def query_tree(self) -> list[int]:
        """Get IDs of all mapped windows in ascending Z order."""
        wids = []

        @ffi.callback("void(int)")
        def loop(wid: int) -> None:
            wids.append(wid)

        lib.qw_server_loop_visible_views(self.qw, loop)
        return wids

    @expose_command()
    def stacking_info(self) -> dict[str, Any]:
        tree = {}
        node_map = {}

        @ffi.callback("void(uintptr_t, uintptr_t, struct scene_node_info)")
        def on_node(node_ptr: ffi.CData, parent_ptr: ffi.CData, info: ffi.CData) -> None:
            node_id = int(node_ptr)
            parent_id = int(parent_ptr) if parent_ptr else None

            node = {
                "name": ffi.string(info.name).decode(),
                "enabled": bool(info.enabled),
                "x": info.x,
                "y": info.y,
                "type": ffi.string(info.type).decode(),
                "wid": getattr(info, "view_wid", None) or None,
                "children": [],
            }

            node_map[node_id] = node

            if parent_id is None:
                tree.update(node)
            else:
                parent = node_map[parent_id]
                parent["children"].append(node)

        lib.qw_server_traverse_scene_graph(self.qw, on_node)

        return tree

    @expose_command()
    @allow_when_locked
    def session_lock_status(self) -> bool:
        """Returns True if server is currently locked."""
        return self._locked

    def check_screen_fullscreen_background(self, screen: Screen | None = None) -> None:
        """Toggles fullscreen background if any window on the screen is fullscreen."""
        if screen is None:
            screens = self.qtile.screens
        else:
            screens = [screen]

        for s in screens:
            if not s.group:
                continue
            enabled = any(w.fullscreen for w in s.group.windows)
            lib.qw_server_set_output_fullscreen_background(self.qw, s.x, s.y, enabled)

    def handle_new_idle_inhibitor(
        self,
        inhibitor: ffi.CData,
        window: Window,
        is_layer_surface: bool,
        is_session_lock_surface: bool,
    ) -> bool:
        return self.inhibitor_manager.add_extension_inhibitor(
            inhibitor, window, is_layer_surface, is_session_lock_surface
        )

    def handle_remove_idle_inhibitor(self, inhibitor: ffi.CData) -> bool:
        return self.inhibitor_manager.remove_extension_inhibitor(inhibitor)

    def check_inhibited(self) -> None:
        self.inhibitor_manager.check()

    def set_inhibited(self, inhibited: bool) -> None:
        if inhibited != self._inhibited:
            hook.fire("idle_inhibitor_change", inhibited)
            self._inhibited = inhibited
            lib.qw_server_set_inhibited(self.qw, inhibited)

    @expose_command()
    def set_idle_inhibitor(self) -> None:
        """Create a global idle inhibitor."""
        self.inhibitor_manager.add_global_inhibitor()

    @expose_command()
    def remove_idle_inhibitor(self) -> None:
        """Remove global idle inhibitor."""
        self.inhibitor_manager.remove_global_inhibitor()

    @expose_command()
    def get_idle_inhibitors(self, active_only: bool = False) -> list[str]:
        """Return list of inhibitors."""
        return [
            f"{inhibitor!r}"
            for inhibitor in self.inhibitor_manager.inhibitors
            if not active_only or (active_only and inhibitor.check())
        ]


class Painter:
    """
    Helper class to manage displaying wallpaper image and solid colours
    on a `Screen`.
    """

    def __init__(self, core: Core):
        self.core = core
        self._mode_map = {
            "stretch": lib.WALLPAPER_MODE_STRETCH,
            "fill": lib.WALLPAPER_MODE_FILL,
            "center": lib.WALLPAPER_MODE_CENTER,
        }

    def fill(self, screen: Screen, background: ColorType) -> None:
        col = ffi.new("float[4]", rgb(background))
        lib.qw_server_paint_background_color(self.core.qw, screen.x, screen.y, col)

    def paint(self, screen: Screen, image_path: str, mode: str | None = None) -> None:
        filename = Path(image_path).expanduser().resolve()
        if not filename.exists():
            logger.warning("Wallpaper image not found: %s", image_path)
            return

        surface = Img.from_path(image_path).default_surface
        surface_pointer = ffi.cast("cairo_surface_t *", surface._pointer)
        w_mode = self._mode_map.get(mode or "stretch", lib.WALLPAPER_MODE_STRETCH)
        lib.qw_server_paint_wallpaper(self.core.qw, screen.x, screen.y, surface_pointer, w_mode)

        # Destroy the surface
        surface.finish()
