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
import time
import typing

import wlroots.helper as wlroots_helper
from pywayland import lib
from pywayland.protocol.wayland import WlSeat
from pywayland.server import Display
from wlroots.wlr_types import (
    Cursor,
    DataDeviceManager,
    GammaControlManagerV1,
    OutputLayout,
    ScreencopyManagerV1,
    Surface,
    XCursorManager,
    XdgOutputManagerV1,
    input_device,
    layer_shell_v1,
    pointer,
    seat,
    xdg_decoration_v1,
)
from wlroots.wlr_types.cursor import WarpMode
from wlroots.wlr_types.virtual_keyboard_v1 import (
    VirtualKeyboardManagerV1,
    VirtualKeyboardV1,
)
from wlroots.wlr_types.xdg_shell import XdgShell, XdgSurface, XdgSurfaceRole
from xkbcommon import xkb

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.wayland import keyboard, window, wlrq
from libqtile.backend.wayland.output import Output
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import List, Optional, Tuple, Union

    from wlroots.wlr_types import Output as wlrOutput

    from libqtile import config, group
    from libqtile.core.manager import Qtile


class Core(base.Core, wlrq.HasListeners):
    def __init__(self):
        """Setup the Wayland core backend"""
        self.qtile: Optional[Qtile] = None
        self.desktops: int = 1
        self.current_desktop: int = 0

        self.display = Display()
        self.event_loop = self.display.get_event_loop()
        self.compositor, self.backend = wlroots_helper.build_compositor(self.display)
        self.renderer = self.backend.renderer
        self.socket = self.display.add_socket()
        self.fd = None

        # set up inputs
        self.keyboards: List[keyboard.Keyboard] = []
        self.grabbed_keys: List[Tuple[int, int]] = []
        self.grabbed_buttons: List[Tuple[int, int]] = []
        self.device_manager = DataDeviceManager(self.display)
        self.seat = seat.Seat(self.display, "seat0")
        self.add_listener(self.seat.request_set_selection_event, self._on_request_set_selection)
        self.add_listener(self.backend.new_input_event, self._on_new_input)

        # set up outputs
        self.output_layout = OutputLayout()
        self.outputs: List[Output] = []
        self.add_listener(self.backend.new_output_event, self._on_new_output)

        # set up cursor
        self.cursor = Cursor(self.output_layout)
        self.cursor_manager = XCursorManager(24)
        self.add_listener(self.seat.request_set_cursor_event, self._on_request_cursor)
        self.add_listener(self.cursor.axis_event, self._on_cursor_axis)
        self.add_listener(self.cursor.frame_event, self._on_cursor_frame)
        self.add_listener(self.cursor.button_event, self._on_cursor_button)
        self.add_listener(self.cursor.motion_event, self._on_cursor_motion)
        self.add_listener(self.cursor.motion_absolute_event, self._on_cursor_motion_absolute)

        # set up shell
        self.xdg_shell = XdgShell(self.display)
        self.add_listener(self.xdg_shell.new_surface_event, self._on_new_xdg_surface)
        self.layer_shell = layer_shell_v1.LayerShellV1(self.display)
        self.add_listener(self.layer_shell.new_surface_event, self._on_new_layer_surface)

        # Add support for additional protocols
        XdgOutputManagerV1(self.display, self.output_layout)
        ScreencopyManagerV1(self.display)
        GammaControlManagerV1(self.display)
        self._virtual_keyboard_manager_v1 = VirtualKeyboardManagerV1(self.display)
        self.add_listener(
            self._virtual_keyboard_manager_v1.new_virtual_keyboard_event,
            self._on_new_virtual_keyboard
        )
        xdg_decoration_manager_v1 = xdg_decoration_v1.XdgDecorationManagerV1.create(self.display)
        self.add_listener(
            xdg_decoration_manager_v1.new_toplevel_decoration_event,
            self._on_new_toplevel_decoration,
        )

        # start
        os.environ["WAYLAND_DISPLAY"] = self.socket.decode()
        logger.info("Starting core with WAYLAND_DISPLAY=" + self.socket.decode())
        self.backend.start()

    def finalize(self):
        for kb in self.keyboards:
            kb.finalize()
        for out in self.outputs:
            out.finalize()

        self.finalize_listeners()
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
            wlr_output.commit()

        self.outputs.append(Output(self, wlr_output))
        self.output_layout.add_auto(wlr_output)

    def _on_request_cursor(self, _listener, event: seat.PointerRequestSetCursorEvent):
        logger.debug("Signal: seat request_set_cursor_event")
        # if self._seat.pointer_state.focused_surface == event.seat_client:  # needs updating pywlroots first
        self.cursor.set_surface(event.surface, event.hotspot)

    def _on_new_xdg_surface(self, _listener, surface: XdgSurface):
        logger.debug("Signal: xdg_shell new_surface_event")
        assert self.qtile is not None

        if surface.role != XdgSurfaceRole.TOPLEVEL:
            return

        wid = max(self.qtile.windows_map.keys(), default=0) + 1
        win = window.Window(self, self.qtile, surface, wid)
        logger.info(f"Managing new top-level window with window ID: {wid}")
        self.qtile.manage(win)

    def _on_cursor_axis(self, _listener, event: pointer.PointerEventAxis):
        logger.debug("Signal: cursor axis")
        self.seat.pointer_notify_axis(
            event.time_msec, event.orientation, event.delta, event.delta_discrete, event.source,
        )

    def _on_cursor_frame(self, _listener, _data):
        logger.debug("Signal: cursor frame")
        self.seat.pointer_notify_frame()

    def _on_cursor_button(self, _listener, event: pointer.PointerEventButton):
        assert self.qtile is not None
        logger.debug("Signal: cursor button")
        self.seat.pointer_notify_button(
            event.time_msec, event.button, event.button_state
        )

        state = self.seat.keyboard.modifier
        button = wlrq.buttons_inv.get(event.button)
        if event.button_state == input_device.ButtonState.PRESSED:
            self.qtile.process_button_click(button, state, self.cursor.x, self.cursor.y, event)
        else:
            self.qtile.process_button_release(button, state)

    def _on_cursor_motion(self, _listener, event: pointer.PointerEventMotion):
        assert self.qtile is not None
        logger.debug("Signal: cursor motion")
        self.cursor.move(event.delta_x, event.delta_y, input_device=event.device)
        self._process_cursor_motion(event.time_msec)

    def _on_cursor_motion_absolute(self, _listener, event: pointer.PointerEventMotionAbsolute):
        assert self.qtile is not None
        logger.debug("Signal: cursor motion_absolute")
        self.cursor.warp(
            WarpMode.AbsoluteClosest, event.x, event.y, input_device=event.device,
        )
        self._process_cursor_motion(event.time_msec)

    def _on_new_virtual_keyboard(self, _listener, virtual_keyboard: VirtualKeyboardV1):
        self._add_new_keyboard(virtual_keyboard.input_device)

    def _on_new_layer_surface(self, _listener, layer_surface: layer_shell_v1.LayerSurfaceV1):
        logger.debug("Signal: layer_shell new_surface_event")
        assert self.qtile is not None

        wid = max(self.qtile.windows_map.keys(), default=0) + 1
        win = window.Static(self, self.qtile, layer_surface, wid)
        logger.info(f"Managing new layer_shell window with window ID: {wid}")
        self.qtile.manage(win)

    def _on_new_toplevel_decoration(
        self, _listener, decoration: xdg_decoration_v1.XdgToplevelDecorationV1
    ):
        logger.debug("Signal: xdg_decoration new_top_level_decoration")
        decoration.set_mode(xdg_decoration_v1.XdgToplevelDecorationV1Mode.SERVER_SIDE)

    def _process_cursor_motion(self, time):
        self.qtile.process_button_motion(self.cursor.x, self.cursor.y)
        found = self._under_pointer()
        if found:
            win, surface, sx, sy = found
            focus_changed = self.seat.pointer_state.focused_surface != surface
            self.seat.pointer_notify_enter(surface, sx, sy)
            if focus_changed:
                hook.fire("client_mouse_enter", win)
                if self.qtile.config.follow_mouse_focus:
                    if win.group.current_window != win:
                        win.group.focus(win, False)
                    if win.group.screen and self.qtile.current_screen != win.group.screen:
                        self.qtile.focus_screen(win.group.screen.index, False)
                    self.focus_window(win, surface)
            else:
                # The enter event contains coordinates, so we only need to
                # notify on motion if the focus did not change
                self.seat.pointer_notify_motion(time, sx, sy)

        else:
            self.cursor_manager.set_cursor_image("left_ptr", self.cursor)
            self.seat.pointer_clear_focus()

    def _add_new_pointer(self, device: input_device.InputDevice):
        logger.info("Adding new pointer")
        self.cursor.attach_input_device(device)

    def _add_new_keyboard(self, device: input_device.InputDevice):
        logger.info("Adding new keyboard")
        self.keyboards.append(keyboard.Keyboard(self, device))
        self.seat.set_keyboard(device)

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
        if not self.display.destroyed:
            self.display.flush_clients()
            self.event_loop.dispatch(0)
            self.display.flush_clients()

    def focus_window(self, win: window.WindowType, surface: Surface = None):
        if self.seat.destroyed:
            return

        if surface is None and win is not None:
            surface = win.surface.surface

        previous_surface = self.seat.keyboard_state.focused_surface
        if previous_surface == surface:
            return
        self.seat.keyboard_clear_focus()

        if previous_surface is not None and previous_surface.is_xdg_surface:
            # Deactivate the previously focused surface
            previous_xdg_surface = XdgSurface.from_surface(previous_surface)
            previous_xdg_surface.set_activated(False)

        if not win:
            return

        if isinstance(win.surface, layer_shell_v1.LayerSurfaceV1):
            if not win.mapped or not win.surface.current.keyboard_interactive:
                return

        logger.debug("Focussing new window")
        if surface.is_xdg_surface and isinstance(win.surface, XdgSurface):
            win.surface.set_activated(True)
        self.seat.keyboard_notify_enter(surface, self.seat.keyboard)

    def focus_by_click(self, event) -> None:
        found = self._under_pointer()
        if found:
            win, surface, _, _ = found
            self.focus_window(win, surface)

    def _under_pointer(self):
        assert self.qtile is not None

        cx = self.cursor.x
        cy = self.cursor.y

        for win in self.qtile.windows_map.values():
            assert isinstance(win, window.Window)  # mypy is dumb and needs this
            if win.mapped:
                surface, sx, sy = win.surface.surface_at(cx - win.x, cy - win.y)
                if surface:
                    return win, surface, sx, sy
                if win.borderwidth:
                    bw = win.borderwidth
                    if win.x - bw <= cx and win.y - bw <= cy:
                        if cx <= win.x + win.width + bw and cy <= win.y + win.height + bw:
                            return win, win.surface.surface, 0, 0
        return None

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

    def grab_button(self, mouse: config.Mouse) -> int:
        """Configure the backend to grab the mouse event"""
        keysym = wlrq.buttons.get(mouse.button_code)
        assert keysym is not None
        mask_key = wlrq.translate_masks(mouse.modifiers)
        self.grabbed_buttons.append((keysym, mask_key))
        return mask_key

    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""
        self.grabbed_buttons.clear()

    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""

    def warp_pointer(self, x, y) -> None:
        """Warp the pointer to the coordinates in relative to the output layout"""
        self.cursor.warp(WarpMode.LayoutClosest, x, y)

    def flush(self) -> None:
        self._poll()

    def graceful_shutdown(self):
        """Try to close windows gracefully before exiting"""
        assert self.qtile is not None

        for win in self.qtile.windows_map.values():
            win.kill()

        # give everyone a little time to exit and write their state. but don't
        # sleep forever (1s).
        end = time.time() + 1
        while time.time() < end:
            self._poll()
            if not self.qtile.windows_map:
                break

    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal to that specified"""
        success = self.backend.get_session().change_vt(vt)
        if not success:
            logger.warning(f"Could not change VT to: {vt}")
        return success

    @property
    def painter(self):
        return wlrq.Painter(self)

    def output_from_wlr_output(self, wlr_output: wlrOutput) -> Output:
        matched = []
        for output in self.outputs:
            if output.wlr_output == wlr_output:
                matched.append(output)

        assert len(matched) == 1
        return matched[0]
