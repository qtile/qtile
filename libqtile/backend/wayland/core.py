# Copyright (c) 2021-5 Matt Colligan
# Copyright (c) 2025 elParaguayo
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
from typing import TYPE_CHECKING

from libqtile import hook, log_utils
from libqtile.backend import base
from libqtile.backend.wayland.window import Internal, Window, WindowType
from libqtile.command.base import expose_command
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


qw_logger = logging.getLogger("qw")


@ffi.def_extern()
def log_cb(importance: int, formatted_str) -> None:
    """Callback that logs the string at the given level"""
    log_str = ffi.string(formatted_str).decode()
    if importance == lib.WLR_ERROR:
        qw_logger.error(log_str)
    elif importance == lib.WLR_INFO:
        qw_logger.info(log_str)
    elif importance == lib.WLR_DEBUG:
        qw_logger.debug(log_str)


@ffi.def_extern()
def keyboard_key_cb(keysym, mask, userdata):
    core = ffi.from_handle(userdata)
    if core.handle_keyboard_key(keysym, mask):
        return 1
    return 0


@ffi.def_extern()
def manage_view_cb(view, userdata):
    core = ffi.from_handle(userdata)
    core.handle_manage_view(view)


@ffi.def_extern()
def unmanage_view_cb(view, userdata):
    core = ffi.from_handle(userdata)
    core.handle_unmanage_view(view)


@ffi.def_extern()
def cursor_motion_cb(x, y, userdata):
    core = ffi.from_handle(userdata)
    core.handle_cursor_motion(x, y)


@ffi.def_extern()
def cursor_button_cb(button, mask, pressed, x, y, userdata):
    core = ffi.from_handle(userdata)
    if core.handle_cursor_button(button, mask, pressed, x, y):
        return 1
    return 0


@ffi.def_extern()
def on_screen_change_cb(userdata):
    core = ffi.from_handle(userdata)
    core.handle_screen_change()


@ffi.def_extern()
def on_screen_reserve_space_cb(output, userdata):
    core = ffi.from_handle(userdata)
    core.handle_screen_reserve_space(output)


def get_wlr_log_level():
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
        # This is the window under the pointer
        self._hovered_window: WindowType | None = None
        # this Internal window receives keyboard input, e.g. via the Prompt widget.
        self.focused_internal: Internal | None = None

        """Setup the Wayland core backend"""
        log_utils.init_log(logger.level, log_path=log_utils.get_default_log(), logger=qw_logger)
        lib.qw_log_init(get_wlr_log_level(), lib.log_cb)
        self.qw = lib.qw_server_create()
        if not self.qw:
            sys.exit(1)

        self._output_reserved_space = {}
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
        lib.qw_server_start(self.qw)
        self.qw_cursor = lib.qw_server_get_cursor(self.qw)

        self.painter = Painter(self)

    def new_wid(self) -> int:
        """Get a new unique window ID"""
        assert self.qtile is not None
        return max(self.qtile.windows_map.keys(), default=0) + 1

    def on_config_load(self, initial: bool) -> None:
        if initial:
            # This backend does not support restarting
            return

        assert self.qtile is not None

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

        # Apply input device configuration
        if self.qtile.config.wl_input_rules:
            # TODO: configure devices (keyboards, pointers)
            pass

    def handle_screen_change(self):
        hook.fire("screen_change", None)

    def get_screen_for_output(self, output):
        assert self.qtile is not None

        for screen in self.qtile.screens:
            # Outputs alias if they have the same (x, y) and share the same Screen, so
            # we don't need to check the if the width and height match the Screen's.
            if screen.x == output.x and screen.y == output.y:
                return screen

        return self.qtile.current_screen

    def handle_screen_reserve_space(self, output):
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

    def handle_cursor_motion(self, x, y):
        assert self.qtile is not None
        self._focus_pointer(x, y)
        self.qtile.process_button_motion(x, y)

    def handle_cursor_button(self, button, mask, pressed, x, y) -> bool:
        assert self.qtile is not None
        if pressed:
            self._focus_by_click()

            handled = self.qtile.process_button_click(int(button), int(mask), x, y)

            if isinstance(self._hovered_window, Internal):
                self._hovered_window.process_button_click(
                    int(self.qw_cursor.cursor.x - self._hovered_window.x),
                    int(self.qw_cursor.cursor.y - self._hovered_window.y),
                    int(button),
                )

            return handled
        else:
            return self.qtile.process_button_release(button, mask)

    def handle_manage_view(self, view):
        wid = self.new_wid()
        view.wid = wid

        win = Window(self.qtile, view, wid)
        if view.title != ffi.NULL:
            win.name = ffi.string(view.title).decode()
        if view.app_id != ffi.NULL:
            win._wm_class = ffi.string(view.app_id).decode()
        win._float_width = win.width  # todo: should we be using getter/setter for _float_width
        win._float_height = win.height

        self.qtile.manage(win)

    def handle_unmanage_view(self, view):
        assert self.qtile is not None
        self.qtile.unmanage(view.wid)

    def handle_keyboard_key(self, keysym, mask):
        if self.focused_internal:
            self.focused_internal.process_key_press(keysym)
            return True

        if (keysym, mask) not in self.grabbed_keys:
            return False

        assert self.qtile is not None
        if self.qtile.process_key_event(keysym, mask)[1]:
            return True

        return False

    def focus_window(self, win: WindowType) -> None:
        if isinstance(win, base.Internal):
            self.focused_internal = win
            lib.qw_server_keyboard_clear_focus(self.qw)
            return

        if self.focused_internal:
            self.focused_internal = None

        # TODO logic imcomplete
        win._ptr.focus(win._ptr, False)  # What is the second argument?

    def _focus_by_click(self):
        assert self.qtile is not None
        view = self.qw_cursor.view

        if view != ffi.NULL:
            win = self.qtile.windows_map.get(view.wid)

            if self.qtile.config.bring_front_click is True:
                win.bring_to_front()
            elif self.qtile.config.bring_front_click == "floating_only":
                if isinstance(win, base.Window) and win.floating:
                    win.bring_to_front()

            if isinstance(win, base.Static):
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

    def _focus_pointer(self, cx: int, cy: int) -> None:
        assert self.qtile is not None
        view = self.qw_cursor.view

        if view == ffi.NULL:
            return

        win = self.qtile.windows_map.get(view.wid)

        if self._hovered_window is not win:
            # We only want to fire client_mouse_enter once, so check
            # self._hovered_window.
            hook.fire("client_mouse_enter", win)

        if win is not self.qtile.current_window:
            if self.qtile.config.follow_mouse_focus is True:
                if isinstance(win, base.Static):
                    self.qtile.focus_screen(win.screen.index, False)
                else:
                    if win.group and win.group.current_window != win:
                        win.group.focus(win, False)
                    if (
                        win.group
                        and win.group.screen
                        and self.qtile.current_screen != win.group.screen
                    ):
                        self.qtile.focus_screen(win.group.screen.index, False)

        self._hovered_window = win

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
        def loop(x, y, width, height):
            rects.append(ScreenRect(x, y, width, height))

        lib.qw_server_loop_output_dims(self.qw, loop)

        return rects

    def _get_sym_from_code(self, keycode: int) -> str:
        # TODO: test keycodes
        sym = lib.qwu_get_sym_from_code(keycode)
        if not sym:
            raise QtileError("Unable to grab keycode. No active keyboard found.")
        return ffi.string(sym).decode()

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
        self._focus_pointer(int(self.qw_cursor.cursor.x), int(self.qw_cursor.cursor.y))

    @property
    def name(self) -> str:
        return "wayland"

    def setup_listener(self) -> None:
        """Setup a listener for the given qtile instance"""
        logger.debug("Adding io watch")
        self.fd = lib.qw_server_get_event_loop_fd(self.qw)
        if self.fd:
            asyncio.get_running_loop().add_reader(self.fd, self._poll)
            os.environ["WAYLAND_DISPLAY"] = self.display_name
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
        def loop(wid):
            wids.append(wid)

        lib.qw_server_loop_visible_views(self.qw, loop)
        return wids


class Painter:
    """
    Helper class to manage displaying wallpaper image and solid colours
    on a `Screen`.
    """

    def __init__(self, core):
        self.core = core
        self._mode_map = {
            "stretch": lib.WALLPAPER_MODE_STRETCH,
            "fill": lib.WALLPAPER_MODE_FILL,
            "center": lib.WALLPAPER_MODE_CENTER,
        }

    def fill(self, screen, background):
        col = ffi.new("float[4]", rgb(background))
        lib.qw_server_paint_background_color(self.core.qw, screen.x, screen.y, col)

    def paint(self, screen, image_path, mode=None):
        filename = Path(image_path).expanduser().resolve()
        if not filename.exists():
            logger.warning("Wallpaper image not found: %s", image_path)
            return

        surface = Img.from_path(image_path).default_surface
        surface_pointer = ffi.cast("cairo_surface_t *", surface._pointer)
        w_mode = self._mode_map.get(mode, lib.WALLPAPER_MODE_STRETCH)
        lib.qw_server_paint_wallpaper(self.core.qw, screen.x, screen.y, surface_pointer, w_mode)

        # Destroy the surface
        surface.finish()
