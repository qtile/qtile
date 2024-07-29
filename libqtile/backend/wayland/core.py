# Copyright (c) 2021-3 Matt Colligan
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
import functools
import logging
import operator
import signal
import os
import sys
import time
from typing import TYPE_CHECKING

from xkbcommon import xkb

from libqtile import hook, log_utils
from libqtile.backend import base
from libqtile.backend.wayland.window import Internal, Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.log_utils import logger
from libqtile.utils import reap_zombies, rgb, ColorsType, QtileError

ffi = None
lib = None
try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")

if TYPE_CHECKING:
    from libqtile import config
    from libqtile.group import _Group


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
            raise QtileError("unknown modifier: %s" % i)
        masks.append(code)
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


qw_logger = logging.getLogger("qw")


# TODO: credit pywlroots
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


# TODO: credit pywlroots
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
        """Setup the Wayland core backend"""
        log_utils.init_log(logger.level, log_path=log_utils.get_default_log(), logger=qw_logger)
        lib.qw_log_init(get_wlr_log_level(), lib.log_cb)
        self.qw = lib.qw_server_create()
        if not self.qw:
            sys.exit(1)
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
        lib.qw_server_start(self.qw)

    def new_wid(self) -> int:
        """Get a new unique window ID"""
        assert self.qtile is not None
        return max(self.qtile.windows_map.keys(), default=0) + 1

    def handle_screen_change(self):
        hook.fire("screen_change", None)

    def handle_cursor_motion(self, x, y):
        assert self.qtile is not None
        self.qtile.process_button_motion(x, y)

    def handle_cursor_button(self, button, mask, pressed, x, y) -> bool:
        assert self.qtile is not None
        if pressed:
            return self.qtile.process_button_click(int(button), int(mask), x, y)
        else:
            return self.qtile.process_button_release(button, mask)

    def handle_manage_view(self, view):
        wid = self.new_wid()
        view.wid = wid
        win = Window(self.qtile, view, wid)
        self.qtile.manage(win)

    def handle_unmanage_view(self, view):
        assert self.qtile is not None
        self.qtile.unmanage(view.wid)

    def handle_keyboard_key(self, keysym, mask):
        if (keysym, mask) not in self.grabbed_keys:
            return False
        assert self.qtile is not None
        if self.qtile.process_key_event(keysym, mask)[1]:
            return True
        return False

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
            keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = translate_masks(key.modifiers)
        self.grabbed_keys.append((keysym, mask_key))
        return keysym, mask_key

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        if isinstance(key.key, str):
            keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = translate_masks(key.modifiers)
        self.grabbed_keys.remove((keysym, mask_key))
        return keysym, mask_key

    def ungrab_keys(self) -> None:
        self.grabbed_keys.clear()

    def grab_button(self, mouse: config.Mouse) -> int:
        return translate_masks(mouse.modifiers)

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
        raise Exception("TODO: implement")

    @expose_command()
    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal to that specified"""
        raise Exception("TODO: implement")

    @expose_command()
    def hide_cursor(self) -> None:
        """Hide the cursor."""
        raise Exception("TODO: implement")

    @expose_command()
    def unhide_cursor(self) -> None:
        """Unhide the cursor."""
        raise Exception("TODO: implement")

    @expose_command()
    def get_inputs(self) -> dict[str, list[dict[str, str]]]:
        """Get information on all input devices."""
        raise Exception("TODO: implement")

    @expose_command()
    def query_tree(self) -> list[int]:
        """Get IDs of all mapped windows in ascending Z order."""
        raise Exception("TODO: implement")
