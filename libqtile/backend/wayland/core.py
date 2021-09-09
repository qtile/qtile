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
    DataControlManagerV1,
    DataDeviceManager,
    GammaControlManagerV1,
    OutputLayout,
    PrimarySelectionV1DeviceManager,
    ScreencopyManagerV1,
    Surface,
    XCursorManager,
    XdgOutputManagerV1,
    input_device,
    pointer,
    seat,
    xdg_decoration_v1,
)
from wlroots.wlr_types.cursor import WarpMode
from wlroots.wlr_types.layer_shell_v1 import (
    LayerShellV1,
    LayerShellV1Layer,
    LayerSurfaceV1,
)
from wlroots.wlr_types.output_management_v1 import (
    OutputConfigurationHeadV1,
    OutputConfigurationV1,
    OutputManagerV1,
)
from wlroots.wlr_types.server_decoration import (
    ServerDecorationManager,
    ServerDecorationManagerMode,
)
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
    from typing import List, Optional, Sequence, Tuple, Union

    from wlroots.wlr_types import Output as wlrOutput

    from libqtile import config
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
        self._hovered_internal: Optional[window.Internal] = None
        self.focused_internal: Optional[window.Internal] = None

        # These windows have not been mapped yet; they'll get managed when mapped
        self.pending_windows: List[window.WindowType] = []

        # mapped_windows contains just regular windows
        self.mapped_windows: List[window.WindowType] = []  # Ascending in Z
        # stacked_windows also contains layer_shell windows from the current output
        self.stacked_windows: Sequence[window.WindowType] = []  # Ascending in Z
        self._current_output: Optional[Output] = None

        # set up inputs
        self.keyboards: List[keyboard.Keyboard] = []
        self.grabbed_keys: List[Tuple[int, int]] = []
        self.grabbed_buttons: List[Tuple[int, int]] = []
        DataDeviceManager(self.display)
        DataControlManagerV1(self.display)
        self.seat = seat.Seat(self.display, "seat0")
        self.add_listener(
            self.seat.request_set_selection_event, self._on_request_set_selection
        )
        self.add_listener(self.backend.new_input_event, self._on_new_input)

        # set up outputs
        self.outputs: List[Output] = []
        self.add_listener(self.backend.new_output_event, self._on_new_output)
        self.output_layout = OutputLayout()
        self.add_listener(
            self.output_layout.change_event, self._on_output_layout_change
        )
        self.output_manager = OutputManagerV1(self.display)
        self.add_listener(
            self.output_manager.apply_event, self._on_output_manager_apply
        )
        self.add_listener(self.output_manager.test_event, self._on_output_manager_test)

        # set up cursor
        self.cursor = Cursor(self.output_layout)
        self.cursor_manager = XCursorManager(24)
        self.add_listener(self.seat.request_set_cursor_event, self._on_request_cursor)
        self.add_listener(self.cursor.axis_event, self._on_cursor_axis)
        self.add_listener(self.cursor.frame_event, self._on_cursor_frame)
        self.add_listener(self.cursor.button_event, self._on_cursor_button)
        self.add_listener(self.cursor.motion_event, self._on_cursor_motion)
        self.add_listener(
            self.cursor.motion_absolute_event, self._on_cursor_motion_absolute
        )

        # set up shell
        self.xdg_shell = XdgShell(self.display)
        self.add_listener(self.xdg_shell.new_surface_event, self._on_new_xdg_surface)
        self.layer_shell = LayerShellV1(self.display)
        self.add_listener(
            self.layer_shell.new_surface_event, self._on_new_layer_surface
        )

        # Add support for additional protocols
        XdgOutputManagerV1(self.display, self.output_layout)
        ScreencopyManagerV1(self.display)
        GammaControlManagerV1(self.display)
        PrimarySelectionV1DeviceManager(self.display)
        self._virtual_keyboard_manager_v1 = VirtualKeyboardManagerV1(self.display)
        self.add_listener(
            self._virtual_keyboard_manager_v1.new_virtual_keyboard_event,
            self._on_new_virtual_keyboard,
        )
        xdg_decoration_manager_v1 = xdg_decoration_v1.XdgDecorationManagerV1.create(
            self.display
        )
        self.add_listener(
            xdg_decoration_manager_v1.new_toplevel_decoration_event,
            self._on_new_toplevel_decoration,
        )
        # wlr_server_decoration will be removed in a future version of wlroots
        server_decoration_manager = ServerDecorationManager.create(self.display)
        server_decoration_manager.set_default_mode(ServerDecorationManagerMode.SERVER)

        # start
        os.environ["WAYLAND_DISPLAY"] = self.socket.decode()
        logger.info("Starting core with WAYLAND_DISPLAY=" + self.socket.decode())
        self.backend.start()

    @property
    def name(self):
        return "wayland"

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

    def _on_request_set_selection(
        self, _listener, event: seat.RequestSetSelectionEvent
    ):
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
        # Put new output at far right
        layout_geo = self.output_layout.get_box()
        self.output_layout.add(wlr_output, layout_geo.width, 0)

        if not self._current_output:
            self._current_output = self.outputs[0]

    def _on_output_layout_change(self, _listener, _data):
        logger.debug("Signal: output_layout change_event")
        config = OutputConfigurationV1()

        for output in self.outputs:
            box = self.output_layout.get_box(output.wlr_output)
            head = OutputConfigurationHeadV1.create(config, output.wlr_output)
            head.state.x = output.x = box.x
            head.state.y = output.y = box.y
            head.state.enabled = output.wlr_output.enabled
            head.state.mode = output.wlr_output.current_mode

        self.output_manager.set_configuration(config)
        self.outputs.sort(key=lambda o: (o.x, o.y))

    def _on_output_manager_apply(self, _listener, config: OutputConfigurationV1):
        logger.debug("Signal: output_manager apply_event")
        self._output_manager_reconfigure(config, True)

    def _on_output_manager_test(self, _listener, config: OutputConfigurationV1):
        logger.debug("Signal: output_manager test_event")
        self._output_manager_reconfigure(config, False)

    def _on_request_cursor(self, _listener, event: seat.PointerRequestSetCursorEvent):
        logger.debug("Signal: seat request_set_cursor_event")
        self.cursor.set_surface(event.surface, event.hotspot)

    def _on_new_xdg_surface(self, _listener, surface: XdgSurface):
        logger.debug("Signal: xdg_shell new_surface_event")
        if surface.role == XdgSurfaceRole.TOPLEVEL:
            assert self.qtile is not None
            win = window.Window(self, self.qtile, surface)
            self.pending_windows.append(win)

    def _on_cursor_axis(self, _listener, event: pointer.PointerEventAxis):
        handled = False
        if event.delta != 0:
            if event.orientation == pointer.AxisOrientation.VERTICAL:
                button = 5 if 0 < event.delta else 4
            else:
                button = 7 if 0 < event.delta else 6
            handled = self._process_cursor_button(button, True)

        if not handled:
            self.seat.pointer_notify_axis(
                event.time_msec,
                event.orientation,
                event.delta,
                event.delta_discrete,
                event.source,
            )

    def _on_cursor_frame(self, _listener, _data):
        self.seat.pointer_notify_frame()

    def _on_cursor_button(self, _listener, event: pointer.PointerEventButton):
        assert self.qtile is not None
        pressed = event.button_state == input_device.ButtonState.PRESSED
        if pressed:
            self._focus_by_click()

        handled = False

        if event.button in wlrq.buttons:
            button = wlrq.buttons.index(event.button) + 1
            handled = self._process_cursor_button(button, pressed)

        if not handled:
            self.seat.pointer_notify_button(
                event.time_msec, event.button, event.button_state
            )

    def _on_cursor_motion(self, _listener, event: pointer.PointerEventMotion):
        assert self.qtile is not None
        self.cursor.move(event.delta_x, event.delta_y, input_device=event.device)
        self._process_cursor_motion(event.time_msec)

    def _on_cursor_motion_absolute(
        self, _listener, event: pointer.PointerEventMotionAbsolute
    ):
        assert self.qtile is not None
        self.cursor.warp(
            WarpMode.AbsoluteClosest,
            event.x,
            event.y,
            input_device=event.device,
        )
        self._process_cursor_motion(event.time_msec)

    def _on_new_virtual_keyboard(self, _listener, virtual_keyboard: VirtualKeyboardV1):
        self._add_new_keyboard(virtual_keyboard.input_device)

    def _on_new_layer_surface(self, _listener, layer_surface: LayerSurfaceV1):
        logger.debug("Signal: layer_shell new_surface_event")
        assert self.qtile is not None

        wid = self.new_wid()
        win = window.Static(self, self.qtile, layer_surface, wid)
        logger.info(f"Managing new layer_shell window with window ID: {wid}")
        self.qtile.manage(win)

    def _on_new_toplevel_decoration(
        self, _listener, decoration: xdg_decoration_v1.XdgToplevelDecorationV1
    ):
        logger.debug("Signal: xdg_decoration new_top_level_decoration")
        decoration.set_mode(xdg_decoration_v1.XdgToplevelDecorationV1Mode.SERVER_SIDE)

    def _output_manager_reconfigure(
        self, config: OutputConfigurationV1, apply: bool
    ) -> None:
        """
        See if an output configuration would be accepted by the backend, and apply it if
        desired.
        """
        ok = True

        for head in config.heads:
            state = head.state
            wlr_output = state.output

            if state.enabled:
                wlr_output.enable()
                if state.mode:
                    wlr_output.set_mode(state.mode)
                else:
                    wlr_output.set_custom_mode(
                        state.custom_mode.width,
                        state.custom_mode.height,
                        state.custom_mode.refresh,
                    )

                self.output_layout.move(wlr_output, state.x, state.y)
                wlr_output.set_transform(state.transform)
                wlr_output.set_scale(state.scale)
            else:
                wlr_output.enable(enable=False)

            ok = wlr_output.test()
            if not ok:
                break

        for head in config.heads:
            if ok and apply:
                head.state.output.commit()
            else:
                head.state.output.rollback()

        if ok:
            config.send_succeeded()
        else:
            config.send_failed()
        config.destroy()
        hook.fire("screen_change", None)

    def _process_cursor_motion(self, time):
        self.qtile.process_button_motion(self.cursor.x, self.cursor.y)

        if len(self.outputs) > 1:
            current_output = self.output_layout.output_at(
                self.cursor.x, self.cursor.y
            ).data
            if self._current_output is not current_output:
                self._current_output = current_output
                self.stack_windows()

        found = self._under_pointer()

        if found:
            win, surface, sx, sy = found
            if isinstance(win, window.Internal):
                if self._hovered_internal is win:
                    win.process_pointer_motion(
                        self.cursor.x - self._hovered_internal.x,
                        self.cursor.y - self._hovered_internal.y,
                    )
                else:
                    if self._hovered_internal:
                        self._hovered_internal.process_pointer_leave(
                            self.cursor.x - self._hovered_internal.x,
                            self.cursor.y - self._hovered_internal.y,
                        )
                    self.cursor_manager.set_cursor_image("left_ptr", self.cursor)
                    self.seat.pointer_clear_focus()
                    win.process_pointer_enter(self.cursor.x, self.cursor.y)
                    self._hovered_internal = win
                return

            if surface is not None:
                self.seat.pointer_notify_enter(surface, sx, sy)
                if self.seat.pointer_state.focused_surface == surface:
                    self.seat.pointer_notify_motion(time, sx, sy)
            else:
                self.seat.pointer_clear_focus()

            if win is not self.qtile.current_window:
                hook.fire("client_mouse_enter", win)

                if self.qtile.config.follow_mouse_focus:
                    if isinstance(win, window.Static):
                        self.qtile.focus_screen(win.screen.index, False)
                    else:
                        if win.group.current_window != win:
                            win.group.focus(win, False)
                        if (
                            win.group.screen
                            and self.qtile.current_screen != win.group.screen
                        ):
                            self.qtile.focus_screen(win.group.screen.index, False)
                    self.focus_window(win, surface)

            if self._hovered_internal:
                self._hovered_internal = None

        else:
            self.cursor_manager.set_cursor_image("left_ptr", self.cursor)
            self.seat.pointer_clear_focus()
            if self._hovered_internal:
                self._hovered_internal.process_pointer_leave(
                    self.cursor.x - self._hovered_internal.x,
                    self.cursor.y - self._hovered_internal.y,
                )
                self._hovered_internal = None

    def _process_cursor_button(self, button: int, pressed: bool) -> bool:
        assert self.qtile is not None

        if pressed:
            handled = self.qtile.process_button_click(
                button, self.seat.keyboard.modifier, self.cursor.x, self.cursor.y
            )

            if self._hovered_internal:
                self._hovered_internal.process_button_click(
                    self.cursor.x - self._hovered_internal.x,
                    self.cursor.y - self._hovered_internal.y,
                    button,
                )
        else:
            handled = self.qtile.process_button_release(button, self.seat.keyboard.modifier)

            if self._hovered_internal:
                self._hovered_internal.process_button_release(
                    self.cursor.x - self._hovered_internal.x,
                    self.cursor.y - self._hovered_internal.y,
                    button,
                )

        return handled

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

    def new_wid(self) -> int:
        """Get a new unique window ID"""
        assert self.qtile is not None
        return max(self.qtile.windows_map.keys(), default=0) + 1

    def focus_window(
        self, win: window.WindowType, surface: Surface = None, enter: bool = True
    ) -> None:
        if self.seat.destroyed:
            return

        if surface is None and win is not None:
            if isinstance(win, base.Internal):
                self.focused_internal = win
                self.seat.keyboard_clear_focus()
                return
            surface = win.surface.surface

        if self.focused_internal:
            self.focused_internal = None

        previous_surface = self.seat.keyboard_state.focused_surface
        if previous_surface == surface:
            return

        if previous_surface is not None and previous_surface.is_xdg_surface:
            # Deactivate the previously focused surface
            previous_xdg_surface = XdgSurface.from_surface(previous_surface)
            if not win or win.surface != previous_xdg_surface:
                previous_xdg_surface.set_activated(False)

        if not win:
            self.seat.keyboard_clear_focus()
            return

        if isinstance(win.surface, LayerSurfaceV1):
            if not win.surface.current.keyboard_interactive:
                return

        logger.debug("Focussing new window")
        if surface.is_xdg_surface and isinstance(win.surface, XdgSurface):
            win.surface.set_activated(True)

        if enter and self.seat.keyboard._ptr:  # This pointer is NULL when headless
            self.seat.keyboard_notify_enter(surface, self.seat.keyboard)

    def _focus_by_click(self) -> None:
        assert self.qtile is not None
        found = self._under_pointer()

        if found:
            win, surface, _, _ = found

            if self.qtile.config.bring_front_click:
                if (
                    self.qtile.config.bring_front_click != "floating_only"
                    or win.floating
                ):
                    win.cmd_bring_to_front()

            if not isinstance(win, base.Internal):
                if not isinstance(win, base.Static):
                    if win.group and win.group.screen is not self.qtile.current_screen:
                        self.qtile.focus_screen(win.group.screen.index, warp=False)
                    self.qtile.current_group.focus(win, False)

                self.focus_window(win, surface=surface, enter=False)

        else:
            screen = self.qtile.find_screen(self.cursor.x, self.cursor.y)
            if screen:
                self.qtile.focus_screen(screen.index, warp=False)

    def _under_pointer(self):
        assert self.qtile is not None

        cx = self.cursor.x
        cy = self.cursor.y

        for win in reversed(self.stacked_windows):
            if isinstance(win, window.Internal):
                if (
                    win.x <= cx <= win.x + win.width
                    and win.y <= cy <= win.y + win.height
                ):
                    return win, None, 0, 0
            else:
                bw = win.borderwidth
                surface, sx, sy = win.surface.surface_at(
                    cx - win.x - bw, cy - win.y - bw
                )
                if surface:
                    return win, surface, sx, sy
                if bw:
                    if win.x <= cx and win.y <= cy:
                        bw *= 2
                        if (
                            cx <= win.x + win.width + bw
                            and cy <= win.y + win.height + bw
                        ):
                            return win, None, 0, 0
        return None

    def stack_windows(self) -> None:
        """Put all windows of all types in a Z-ordered list."""
        if self._current_output:
            layers = self._current_output.layers
            self.stacked_windows = (
                layers[LayerShellV1Layer.BACKGROUND] +
                layers[LayerShellV1Layer.BOTTOM] +
                self.mapped_windows +  # type: ignore
                layers[LayerShellV1Layer.TOP] +
                layers[LayerShellV1Layer.OVERLAY]
            )
        else:
            self.stacked_windows = self.mapped_windows

    def get_screen_info(self) -> List[Tuple[int, int, int, int]]:
        """Get the screen information"""
        return [
            screen.get_geometry()
            for screen in self.outputs
            if screen.wlr_output.enabled
        ]

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
        keysym = wlrq.buttons[mouse.button_code]
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

    def warp_pointer(self, x: int, y: int) -> None:
        """Warp the pointer to the coordinates in relative to the output layout"""
        self.cursor.warp(WarpMode.LayoutClosest, x, y)

    def flush(self) -> None:
        self._poll()

    def create_internal(self, x: int, y: int, width: int, height: int) -> base.Internal:
        assert self.qtile is not None
        internal = window.Internal(self, self.qtile, x, y, width, height)
        self.qtile.manage(internal)
        return internal

    def graceful_shutdown(self):
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

    def set_keymap(
        self, layout: Optional[str], options: Optional[str], variant: Optional[str]
    ) -> None:
        """
        Set the keymap for the current keyboard.
        """
        if self.keyboards:
            self.keyboards[-1].set_keymap(layout, options, variant)
        else:
            logger.warning("Could not set keymap: no keyboards set up.")

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        return xkb.keysym_from_name(name, case_insensitive=True)

    def simulate_keypress(self, modifiers: List[str], key: str) -> None:
        """Simulates a keypress on the focused window."""
        keysym = xkb.keysym_from_name(key, case_insensitive=True)
        mods = wlrq.translate_masks(modifiers)

        if (keysym, mods) in self.grabbed_keys:
            assert self.qtile is not None
            self.qtile.process_key_event(keysym, mods)
            return

        if self.focused_internal:
            self.focused_internal.process_key_press(keysym)
