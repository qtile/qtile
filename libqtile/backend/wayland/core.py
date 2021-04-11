# Copyright (c) 2021 Matt Colligan
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
import os
import typing

from pywayland import lib
from pywayland.protocol.wayland import WlSeat
from pywayland.server import Display, Listener
from wlroots.backend import Backend
from wlroots.renderer import Renderer
from wlroots.wlr_types import (
    Compositor,
    Cursor,
    DataDeviceManager,
    OutputLayout,
    Surface,
    XCursorManager,
    input_device,
    seat,
    xdg_shell,
)
from xkbcommon import xkb

from libqtile.backend import base
from libqtile.backend.wayland import keyboard, output, window, wlrq
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import List, Optional, Tuple, Union

    from wlroots.wlr_types import Output as wlrOutput

    from libqtile import config, group
    from libqtile.core.manager import Qtile


class Core(base.Core):
    def __init__(self):
        """Setup the Wayland core backend"""
        self.qtile: Optional[Qtile] = None
        self.desktops: int = 1
        self.current_desktop: int = 0

        self.display = Display()
        self.event_loop = self.display.get_event_loop()
        self.backend = Backend(self.display)
        self.renderer = Renderer(self.backend, self.display)
        self.compositor = Compositor(self.display, self.renderer)
        self.socket = self.display.add_socket()
        self.fd = None

        # set up inputs
        self.keyboards: List[keyboard.Keyboard] = []
        self.grabbed_keys: List[Tuple[int, int]] = []
        self.grabbed_buttons: List[Tuple[int, int]] = []
        self.device_manager = DataDeviceManager(self.display)
        self.seat = seat.Seat(self.display, "seat0")
        self._on_request_set_selection_listener = Listener(self._on_request_set_selection)
        self._on_new_input_listener = Listener(self._on_new_input)
        self.seat.request_set_selection_event.add(self._on_request_set_selection_listener)
        self.backend.new_input_event.add(self._on_new_input_listener)

        # set up outputs
        self.output_layout = OutputLayout()
        self.outputs: List[output.Output] = []
        self._on_new_output_listener = Listener(self._on_new_output)
        self.backend.new_output_event.add(self._on_new_output_listener)

        # set up cursor
        self.cursor = Cursor(self.output_layout)
        self.cursor_manager = XCursorManager(24)
        self._on_request_cursor_listener = Listener(self._on_request_cursor)
        self.seat.request_set_cursor_event.add(self._on_request_cursor_listener)

        # set up shell
        self.windows: List[window.Window] = []
        self.xdg_shell = xdg_shell.XdgShell(self.display)
        self._on_new_xdg_surface_listener = Listener(self._on_new_xdg_surface)
        self.xdg_shell.new_surface_event.add(self._on_new_xdg_surface_listener)

        # start
        os.environ["WAYLAND_DISPLAY"] = self.socket.decode()
        logger.info("Starting core with WAYLAND_DISPLAY=" + self.socket.decode())
        self.backend.start()

    def finalize(self):
        self._on_new_xdg_surface_listener.remove()
        self._on_request_cursor_listener.remove()
        self._on_new_output_listener.remove()
        self._on_new_input_listener.remove()
        self._on_request_set_selection_listener.remove()

        for win in self.windows:
            win.finalize()
        for kb in self.keyboards:
            kb.finalize()
        for out in self.outputs:
            out.finalize()

        self.cursor_manager.destroy()
        self.cursor.destroy()
        self.output_layout.destroy()
        self.seat.destroy()
        self.backend.destroy()
        self.display.destroy()
        self.qtile = None

    @property
    def display_name(self) -> str:
        return self.socket.decode()

    def _on_request_set_selection(self, _listener, event: seat.RequestSetSelectionEvent):
        self.seat.set_selection(event._ptr.source, event.serial)
        logger.debug("Signal: seat request_set_selection")

    def _on_new_input(self, _listener, device: input_device.InputDevice):
        logger.debug("Signal: backend new_input_event")
        if device.device_type == input_device.InputDeviceType.POINTER:
            self._add_new_pointer(device)
        elif device.device_type == input_device.InputDeviceType.KEYBOARD:
            self._add_new_keyboard(device)

        capabilities = WlSeat.capability.pointer
        if len(self.keyboards) > 0:
            capabilities |= WlSeat.capability.keyboard

        logger.info("New input: " + str(device.device_type))
        logger.info("Input capabilities: " + str(capabilities))

        self.seat.set_capabilities(capabilities)

    def _on_new_output(self, _listener, wlr_output: wlrOutput):
        logger.debug("Signal: backend new_output_event")
        if wlr_output.modes != []:
            mode = wlr_output.preferred_mode()
            if mode is None:
                logger.error("New output has no output mode")
                return
            wlr_output.set_mode(mode)
            wlr_output.enable()

            if not wlr_output.commit():
                logger.error("New output cannot be committed")
                return

        self.outputs.append(output.Output(self, wlr_output))
        self.output_layout.add_auto(wlr_output)

    def _on_request_cursor(self, _listener, event: seat.PointerRequestSetCursorEvent):
        logger.debug("Signal: seat request_set_cursor_event")
        # if self._seat.pointer_state.focused_surface == event.seat_client:  # needs updating pywlroots first
        self.cursor.set_surface(event.surface, event.hotspot)

    def _on_new_xdg_surface(self, _listener, surface: xdg_shell.XdgSurface):
        logger.debug("Signal: xdg_shell new_surface_event")
        assert self.qtile is not None

        if surface.role != xdg_shell.XdgSurfaceRole.TOPLEVEL:
            return

        logger.info("Managing new top-level window")
        self.windows.append(window.Window(self, surface))

    def _add_new_pointer(self, device: input_device.InputDevice):
        logger.info("Adding new pointer")
        self.cursor.attach_input_device(device)

    def _add_new_keyboard(self, device: input_device.InputDevice):
        logger.info("Adding new keyboard")
        self.keyboards.append(keyboard.Keyboard(self, device))
        self.seat.set_keyboard(device)

    def focus_window(self, win: window.Window, surface: Surface = None):
        if surface is None:
            surface = win.surface.surface

        previous_surface = self.seat.keyboard_state.focused_surface
        if previous_surface == surface:
            return

        if previous_surface is not None:
            # Deactivate the previously focused surface
            previous_xdg_surface = xdg_shell.XdgSurface.from_surface(previous_surface)
            previous_xdg_surface.set_activated(False)

        # roll the given surface to the front of the list, copy and modify the
        # list, then save back to prevent any race conditions on list
        # modification
        windows = self.windows[:]
        windows.remove(win)
        windows.append(win)
        self.win = windows
        # activate the new surface
        win.surface.set_activated(True)
        self.seat.keyboard_notify_enter(surface, self.seat.keyboard)
        logger.debug("Focussed new window")

    def setup_listener(self, qtile: Qtile) -> None:
        """Setup a listener for the given qtile instance"""
        logger.debug("Adding io watch")
        self.qtile = qtile
        self.fd = lib.wl_event_loop_get_fd(self.event_loop._ptr)
        asyncio.get_running_loop().add_reader(self.fd, self._poll)

    def remove_listener(self) -> None:
        """Remove the listener from the given event loop"""
        if self.fd is not None:
            logger.debug("Removing io watch")
            loop = asyncio.get_running_loop()
            loop.remove_reader(self.fd)
            self.fd = None

    def _poll(self) -> None:
        self.display.flush_clients()
        self.event_loop.dispatch(-1)

    def update_desktops(self, groups: List[group._Group], index: int) -> None:
        """Set the current desktops of the window manager

        The list of desktops is given by the list of groups, with the current
        desktop given by the index
        """
        new_count = len(groups)
        while new_count > self.desktops:
            self.desktops += 1
        while new_count < self.desktops:
            self.desktops -= 1
        self.current_desktop = index

    def get_screen_info(self) -> List[Tuple[int, int, int, int]]:
        """Get the screen information"""
        return [screen.get_geometry() for screen in self.outputs]

    def grab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Configure the backend to grab the key event"""
        keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        mask_key = wlrq.translate_masks(key.modifiers)
        self.grabbed_keys.append((keysym, mask_key))
        return keysym, mask_key

    def ungrab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Release the given key event"""
        keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        mask_key = wlrq.translate_masks(key.modifiers)
        self.grabbed_keys.remove((keysym, mask_key))
        return keysym, mask_key

    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""
        self.grabbed_keys.clear()

    def grab_button(self, mouse: config.Mouse) -> None:
        """Configure the backend to grab the mouse event"""
        keysym = wlrq.buttons.get(mouse.button)
        assert keysym is not None
        mask_key = wlrq.translate_masks(mouse.modifiers)
        self.grabbed_buttons.append((keysym, mask_key))

    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""
        self.grabbed_buttons.clear()

    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""
