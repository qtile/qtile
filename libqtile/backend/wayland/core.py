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
import contextlib
import os
import signal
import time
from collections import defaultdict
from typing import TYPE_CHECKING, cast

import pywayland
import pywayland.server
import wlroots.helper as wlroots_helper
import wlroots.wlr_types.virtual_keyboard_v1 as vkeyboard
import wlroots.wlr_types.virtual_pointer_v1 as vpointer
from pywayland.protocol.wayland import WlSeat
from pywayland.utils import wl_container_of
from wlroots import xwayland
from wlroots.util import log as wlr_log
from wlroots.util.box import Box
from wlroots.wlr_types import (
    DataControlManagerV1,
    DataDeviceManager,
    ExportDmabufManagerV1,
    ForeignToplevelManagerV1,
    FractionalScaleManagerV1,
    GammaControlManagerV1,
    InputInhibitManager,
    OutputLayout,
    OutputState,
    PointerGesturesV1,
    Presentation,
    PrimarySelectionV1DeviceManager,
    RelativePointerManagerV1,
    ScreencopyManagerV1,
    Surface,
    Viewporter,
    XCursorManager,
    XdgOutputManagerV1,
    input_device,
    pointer,
    seat,
    xdg_activation_v1,
    xdg_decoration_v1,
)
from wlroots.wlr_types.cursor import Cursor, WarpMode
from wlroots.wlr_types.idle_inhibit_v1 import IdleInhibitorManagerV1, IdleInhibitorV1
from wlroots.wlr_types.idle_notify_v1 import IdleNotifierV1
from wlroots.wlr_types.keyboard import Keyboard
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1, LayerSurfaceV1
from wlroots.wlr_types.output_management_v1 import (
    OutputConfigurationHeadV1,
    OutputConfigurationV1,
    OutputManagerV1,
)
from wlroots.wlr_types.output_power_management_v1 import (
    OutputPowerManagementV1Mode,
    OutputPowerManagerV1,
    OutputPowerV1SetModeEvent,
)
from wlroots.wlr_types.pointer_constraints_v1 import PointerConstraintsV1, PointerConstraintV1
from wlroots.wlr_types.scene import (
    Scene,
    SceneBuffer,
    SceneNode,
    SceneNodeType,
    SceneRect,
    SceneSurface,
    SceneTree,
)
from wlroots.wlr_types.server_decoration import (
    ServerDecorationManager,
    ServerDecorationManagerMode,
)
from wlroots.wlr_types.xdg_shell import XdgShell, XdgSurface, XdgSurfaceRole
from xkbcommon import xkb

from libqtile import hook, log_utils
from libqtile.backend import base
from libqtile.backend.wayland import inputs, layer, window, wlrq, xdgwindow, xwindow
from libqtile.backend.wayland.output import Output
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.log_utils import logger
from libqtile.utils import QtileError, reap_zombies

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any

    from cairocffi import ImageSurface
    from pywayland.server import Listener
    from wlroots.wlr_types import Output as wlrOutput
    from wlroots.wlr_types.data_device_manager import Drag

    from libqtile import config


class ImplicitGrab(wlrq.HasListeners):
    """Keep track of an implicit pointer grab.

    A Wayland client expects to receive pointer events from the moment a
    pointer button is pressed on its surface until the moment the button is
    released.  The Wayland protocol leaves this behavior to the compositor.
    """

    def __init__(
        self,
        core: Core,
        surface: Surface,
        start_x: int,
        start_y: int,
        start_sx: int,
        start_sy: int,
    ) -> None:
        self.core = core
        self.surface = surface
        self.start_dx = start_sx - start_x
        self.start_dy = start_sy - start_y
        self.add_listener(surface.destroy_event, self._on_destroy)

    def finalize(self) -> None:
        self.finalize_listeners()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        self.core._release_implicit_grab()


class Core(base.Core, wlrq.HasListeners):
    supports_restarting: bool = False

    def __init__(self) -> None:
        """Setup the Wayland core backend"""
        # This is the window under the pointer
        self._hovered_window: window.WindowType | None = None
        # but this Internal receives keyboard input, e.g. via the Prompt widget.
        self.focused_internal: window.Internal | None = None

        # Log exceptions that are raised in Wayland callback functions.
        log_utils.init_log(
            logger.level,
            log_path=log_utils.get_default_log(),
            logger=pywayland.server.listener.logger,
        )
        wlr_log.log_init(logger.level)
        log_utils.init_log(
            logger.level,
            log_path=log_utils.get_default_log(),
            logger=wlr_log.logger,
        )

        self.fd: int | None = None
        self.display = pywayland.server.display.Display()
        self.event_loop = self.display.get_event_loop()
        (
            self.compositor,
            self.allocator,
            self.renderer,
            self.backend,
            self._subcompositor,
        ) = wlroots_helper.build_compositor(self.display)
        self.socket = self.display.add_socket()
        os.environ["WAYLAND_DISPLAY"] = self.socket.decode()
        logger.info("Start core with WAYLAND_DISPLAY=%s", os.environ["WAYLAND_DISPLAY"])

        # These windows have not been mapped yet; they'll get managed when mapped
        self.pending_windows: set[window.WindowType] = set()

        # Set up inputs
        self.keyboards: list[inputs.Keyboard] = []
        self._pointers: list[inputs.Pointer] = []
        self.grabbed_keys: list[tuple[int, int]] = []
        DataDeviceManager(self.display)
        self.live_dnd: wlrq.Dnd | None = None
        DataControlManagerV1(self.display)
        self.seat = seat.Seat(self.display, "seat0")
        self.add_listener(self.seat.request_set_selection_event, self._on_request_set_selection)
        self.add_listener(
            self.seat.request_set_primary_selection_event, self._on_request_set_primary_selection
        )
        self.add_listener(self.seat.request_start_drag_event, self._on_request_start_drag)
        self.add_listener(self.seat.start_drag_event, self._on_start_drag)
        self.add_listener(self.backend.new_input_event, self._on_new_input)
        # Some devices are added early, so we need to remember to configure them
        self._pending_input_devices: list[inputs._Device] = []
        hook.subscribe.startup_complete(self._configure_pending_inputs)

        self._input_inhibit_manager = InputInhibitManager(self.display)
        self.add_listener(
            self._input_inhibit_manager.activate_event, self._on_input_inhibitor_activate
        )
        self.add_listener(
            self._input_inhibit_manager.deactivate_event, self._on_input_inhibitor_deactivate
        )
        # exclusive_layer: this layer shell window holds keyboard focus when above other
        # (layer or non-layer) windows, per the layer shell protocol.
        self.exclusive_layer: layer.LayerStatic | None = None
        # exclusive_client: this client (any shell) absorbs keyboard AND pointer input,
        # per input inhibitor protocol.
        self.exclusive_client: pywayland.server.Client | None = None

        # Set up outputs
        self._outputs: list[Output] = []
        self._current_output: Output | None = None
        self.add_listener(self.backend.new_output_event, self._on_new_output)
        self.output_layout = OutputLayout()
        self.add_listener(self.output_layout.change_event, self._on_output_layout_change)
        self.output_manager = OutputManagerV1(self.display)
        self.add_listener(self.output_manager.apply_event, self._on_output_manager_apply)
        self.add_listener(self.output_manager.test_event, self._on_output_manager_test)
        self._blanked_outputs: set[Output] = set()

        # Set up cursor
        self.cursor = Cursor(self.output_layout)
        # we later load a new cursor manager with the config settings
        self._cursor_manager = XCursorManager(None, 24)
        self._gestures = PointerGesturesV1(self.display)
        self._pressed_button_count = 0
        self._implicit_grab: ImplicitGrab | None = None
        self.add_listener(self.seat.request_set_cursor_event, self._on_request_cursor)
        self.add_listener(self.cursor.axis_event, self._on_cursor_axis)
        self.add_listener(self.cursor.frame_event, self._on_cursor_frame)
        self.add_listener(self.cursor.button_event, self._on_cursor_button)
        self.add_listener(self.cursor.motion_event, self._on_cursor_motion)
        self.add_listener(self.cursor.motion_absolute_event, self._on_cursor_motion_absolute)
        self.add_listener(self.cursor.pinch_begin, self._on_cursor_pinch_begin)
        self.add_listener(self.cursor.pinch_update, self._on_cursor_pinch_update)
        self.add_listener(self.cursor.pinch_end, self._on_cursor_pinch_end)
        self.add_listener(self.cursor.swipe_begin, self._on_cursor_swipe_begin)
        self.add_listener(self.cursor.swipe_update, self._on_cursor_swipe_update)
        self.add_listener(self.cursor.swipe_end, self._on_cursor_swipe_end)
        self.add_listener(self.cursor.hold_begin, self._on_cursor_hold_begin)
        self.add_listener(self.cursor.hold_end, self._on_cursor_hold_end)
        self._cursor_state = wlrq.CursorState()

        # Set up shell
        self.xdg_shell = XdgShell(self.display)
        self.add_listener(self.xdg_shell.new_surface_event, self._on_new_xdg_surface)
        self.layer_shell = LayerShellV1(self.display, 4)
        self.add_listener(self.layer_shell.new_surface_event, self._on_new_layer_surface)

        # Set up scene-graph tree, which looks like this from bottom to top:
        #
        #     root (self.scene)
        #     │
        #     ├── self.wallpaper_tree
        #     │   ├── SceneBuffer in self.wallpapers
        #     │   └── ... (further outputs)
        #     │
        #     ├── self.windows_tree
        #     │   │
        #     │   ├── Background (layer shell)
        #     │   │   ├── LayerStatic.tree
        #     │   │   └── ...
        #     │   │
        #     │   ├── Bottom (layer shell)
        #     │   │   ├── LayerStatic.tree
        #     │   │   └── ...
        #     │   │
        #     │   ├── self.mid_window_tree
        #     │   │   ├── XdgWindow.container
        #     │   │   │   ├── XdgWindow.tree
        #     │   │   │   └── XdgWindow._borders
        #     │   │   ├── XWindow.container
        #     │   │   │   ├── XWindow.tree
        #     │   │   │   └── XWindow._borders
        #     │   │   └── ... (further regular windows)
        #     │   │
        #     │   ├── Top (same as Background)
        #     │   │   ├── LayerStatic.tree
        #     │   │   └── ...
        #     │   │
        #     │   └── Overlay (same as Background)
        #     │       ├── LayerStatic.tree
        #     │       └── ...
        #     │
        #     └── self.drag_icon_tree
        #         ├── DragIcon
        #         │   └── wlrq.Dnd
        #         └── ... (usually only one)
        #
        self.scene = Scene()
        # Each tree is created above existing trees
        self.wallpaper_tree = SceneTree.create(self.scene.tree)
        self.windows_tree = SceneTree.create(self.scene.tree)
        self.drag_icon_tree = SceneTree.create(self.scene.tree)
        self.layer_trees = [
            SceneTree.create(self.windows_tree),  # Background
            SceneTree.create(self.windows_tree),  # Bottom
            SceneTree.create(self.windows_tree),  # Regular windows
            SceneTree.create(self.windows_tree),  # Top
            SceneTree.create(self.windows_tree),  # Overlay
        ]
        self.mid_window_tree = self.layer_trees.pop(2)
        self.wallpapers: dict[
            config.Screen, tuple[SceneBuffer | SceneRect, ImageSurface | None]
        ] = {}

        # Add support for additional protocols
        ExportDmabufManagerV1(self.display)
        XdgOutputManagerV1(self.display, self.output_layout)
        ScreencopyManagerV1(self.display)
        GammaControlManagerV1(self.display)
        Viewporter(self.display)
        FractionalScaleManagerV1(self.display)
        self.scene.set_presentation(Presentation.create(self.display, self.backend))
        output_power_manager = OutputPowerManagerV1(self.display)
        self.add_listener(
            output_power_manager.set_mode_event, self._on_output_power_manager_set_mode
        )
        self.idle = IdleNotifierV1(self.display)
        idle_ihibitor_manager = IdleInhibitorManagerV1(self.display)
        self.add_listener(idle_ihibitor_manager.new_inhibitor_event, self._on_new_idle_inhibitor)
        PrimarySelectionV1DeviceManager(self.display)
        virtual_keyboard_manager_v1 = vkeyboard.VirtualKeyboardManagerV1(self.display)
        self.add_listener(
            virtual_keyboard_manager_v1.new_virtual_keyboard_event,
            self._on_new_virtual_keyboard,
        )
        virtual_pointer_manager_v1 = vpointer.VirtualPointerManagerV1(self.display)
        self.add_listener(
            virtual_pointer_manager_v1.new_virtual_pointer_event,
            self._on_new_virtual_pointer,
        )
        xdg_decoration_manager_v1 = xdg_decoration_v1.XdgDecorationManagerV1.create(self.display)
        self.add_listener(
            xdg_decoration_manager_v1.new_toplevel_decoration_event,
            self._on_new_toplevel_decoration,
        )
        # wlr_server_decoration will be removed in a future version of wlroots
        server_decoration_manager = ServerDecorationManager.create(self.display)
        server_decoration_manager.set_default_mode(ServerDecorationManagerMode.SERVER)
        pointer_constraints_v1 = PointerConstraintsV1(self.display)
        self.add_listener(
            pointer_constraints_v1.new_constraint_event,
            self._on_new_pointer_constraint,
        )
        self.pointer_constraints: set[window.PointerConstraint] = set()
        self.active_pointer_constraint: window.PointerConstraint | None = None
        self._relative_pointer_manager_v1 = RelativePointerManagerV1(self.display)
        self.foreign_toplevel_manager_v1 = ForeignToplevelManagerV1.create(self.display)

        self._xdg_activation_v1 = xdg_activation_v1.XdgActivationV1.create(self.display)
        self.add_listener(
            self._xdg_activation_v1.request_activate_event,
            self._on_xdg_activation_v1_request_activate,
        )

        # Set up XWayland. wlroots wants to fork() and waitpid() for the
        # xwayland server:
        # https://gitlab.freedesktop.org/wlroots/wlroots/-/commit/871646d22522141c45db2c0bfa1528d595bb69df
        # so we need to delay installing our SIGCHLD handler so they can
        # actually waitpid(). we install it in _on_xwayland_ready() or the
        # exception handler, whichever is executed. This can be reverted if/when:
        # https://gitlab.freedesktop.org/wlroots/wlroots/-/merge_requests/4926
        # is merged.
        self._xwayland: xwayland.XWayland | None = None
        try:
            self._xwayland = xwayland.XWayland(self.display, self.compositor, True)
        except RuntimeError:
            logger.info("Failed to set up XWayland. Continuing without.")
            asyncio.get_running_loop().add_signal_handler(signal.SIGCHLD, reap_zombies)
        else:
            os.environ["DISPLAY"] = self._xwayland.display_name or ""
            logger.info("Set up XWayland with DISPLAY=%s", os.environ["DISPLAY"])
            self.add_listener(self._xwayland.ready_event, self._on_xwayland_ready)
            self.add_listener(self._xwayland.new_surface_event, self._on_xwayland_new_surface)

        # Start
        self.backend.start()

    def get_enabled_outputs(self) -> list[Output]:
        ret = []
        for output in self._outputs:
            if not output.wlr_output:
                continue
            if not output.wlr_output.enabled:
                continue
            ret.append(output)
        return ret

    @property
    def name(self) -> str:
        return "wayland"

    @property
    def active_keyboard(self) -> inputs.Keyboard | None:
        keyboard = self.seat.get_keyboard()
        if keyboard is not None:
            for kb in self.keyboards:
                if kb.keyboard._ptr == keyboard._ptr:
                    return kb

        return None

    def finalize(self) -> None:
        self.finalize_listeners()
        self._poll()
        for kb in self.keyboards.copy():
            kb.finalize()
        for pt in self._pointers.copy():
            pt.finalize()
        for out in self._outputs.copy():
            out.finalize()

        if self._xwayland:
            self._xwayland.destroy()
        self._cursor_manager.destroy()
        self.cursor.destroy()
        self.output_layout.destroy()
        self.seat.destroy()
        self.backend.destroy()
        self.display.destroy()
        if hasattr(self, "qtile"):
            delattr(self, "qtile")

    def win_from_node(self, node: SceneNode) -> window.Window | window.Internal:
        tree = node.parent
        while tree and tree.node.data is None:
            tree = tree.node.parent
        assert tree and tree.node.data
        return tree.node.data

    # Low level iteration code
    # We cannot use for_each_buffer I think because that does not give the underlying nodes
    # We need to underlying nodes to get the opacity property
    def configure_node_opacity(self, node: SceneNode) -> None:
        if not node.enabled:
            return
        if node.type == SceneNodeType.BUFFER:
            scene_buffer = SceneBuffer.from_node(node)
            win = self.win_from_node(node)
            scene_buffer.set_opacity(win.opacity)
        elif node.type == SceneNodeType.TREE:
            tree_ptr = wl_container_of(node._ptr, "struct wlr_scene_tree *", "node", ffi=ffi)
            parent_tree = SceneTree(tree_ptr)
            for child in parent_tree.children:
                self.configure_node_opacity(child)

    @property
    def display_name(self) -> str:
        return os.environ.get("WAYLAND_DISPLAY", "")

    @property
    def xdisplay_name(self) -> str:
        return os.environ.get("DISPLAY", "")

    def _on_request_set_selection(
        self, _listener: Listener, event: seat.RequestSetSelectionEvent
    ) -> None:
        self.seat.set_selection(event._ptr.source, event.serial)
        logger.debug("Signal: seat request_set_selection")

    def _on_request_set_primary_selection(
        self, _listener: Listener, event: seat.RequestSetPrimarySelectionEvent
    ) -> None:
        self.seat.set_primary_selection(event._ptr.source, event.serial)
        logger.debug("Signal: seat request_set_primary_selection")

    def _on_request_start_drag(
        self, _listener: Listener, event: seat.RequestStartDragEvent
    ) -> None:
        logger.debug("Signal: seat request_start_drag")

        if not self.live_dnd and self.seat.validate_pointer_grab_serial(
            event.origin, event.serial
        ):
            self.seat.start_pointer_drag(event.drag, event.serial)
        else:
            event.drag.source.destroy()

    def _on_start_drag(self, _listener: Listener, wlr_drag: Drag) -> None:
        logger.debug("Signal: seat start_drag")
        self._release_implicit_grab()
        if not wlr_drag.icon:
            return
        self.live_dnd = wlrq.Dnd(self, wlr_drag)

    def _on_new_input(self, _listener: Listener, wlr_device: input_device.InputDevice) -> None:
        logger.debug("Signal: backend new_input_event")

        device: inputs._Device
        if wlr_device.type == input_device.InputDeviceType.POINTER:
            device = self._add_new_pointer(wlr_device)
        elif wlr_device.type == input_device.InputDeviceType.KEYBOARD:
            device = self._add_new_keyboard(wlr_device)
        else:
            logger.info("New %s device", wlr_device.type.name)
            return

        capabilities = WlSeat.capability.pointer
        if self.keyboards:
            capabilities |= WlSeat.capability.keyboard
        self.seat.set_capabilities(capabilities)

        logger.info("New device: %s %s", *device.get_info())
        if hasattr(self, "qtile"):
            if self.qtile.config.wl_input_rules:
                device.configure(self.qtile.config.wl_input_rules)
        else:
            self._pending_input_devices.append(device)

    def _on_new_output(self, _listener: Listener, wlr_output: wlrOutput) -> None:
        logger.debug("Signal: backend new_output_event")
        output = Output(self, wlr_output)
        self._outputs.append(output)

        # Let the output layout place it
        if not self.output_layout.add_auto(wlr_output):
            logger.warning("Failed to add output to layout.")
            return

        # Set the current output as we have none defined
        # Now that we have our first output we can warp the pointer there too
        # We also set the cursor image as we're initializing the cursor here anyways
        if not self._current_output:
            self._current_output = output
            self.cursor.set_xcursor(self._cursor_manager, "default")
            rect = output.get_screen_info()
            box = Box(rect.x, rect.y, rect.width, rect.height)
            x = box.x + box.width / 2
            y = box.y + box.height / 2
            self.warp_pointer(x, y)

    def _on_output_layout_change(
        self, _listener: Listener | None = None, _data: Any = None
    ) -> None:
        logger.debug("Signal: output_layout change_event")
        config = OutputConfigurationV1()

        # disable mons that are no longer enabled
        for output in self._outputs:
            if output.wlr_output.enabled:
                continue
            head = OutputConfigurationHeadV1.create(config, output.wlr_output)
            head.state.enabled = False
            self.output_layout.remove(output.wlr_output)
            if output is self._current_output:
                en_outputs = self.get_enabled_outputs()
                self._current_output = en_outputs[0] if en_outputs else None

        for output in self._outputs:
            if not output.wlr_output.enabled:
                continue
            box = self.output_layout.get_box(output.wlr_output)
            if lib.wlr_box_empty(box._ptr):
                self.output_layout.add_auto(output.wlr_output)

        # add monitors to layout that are now enabled
        for output in self._outputs:
            if not output.wlr_output.enabled:
                continue
            head = OutputConfigurationHeadV1.create(config, output.wlr_output)
            box = self.output_layout.get_box(output.wlr_output)
            head.state.x = output.x = box.x
            head.state.y = output.y = box.y
            head.state.enabled = not lib.wlr_box_empty(box._ptr)
            output.scene_output.set_position(output.x, output.y)

        self.output_manager.set_configuration(config)
        self._outputs.sort(key=lambda o: (o.x, o.y))
        hook.fire("screen_change", None)

    def _on_output_manager_apply(
        self, _listener: Listener, config: OutputConfigurationV1
    ) -> None:
        logger.debug("Signal: output_manager apply_event")
        self._output_manager_reconfigure(config, True)

    def _on_output_manager_test(self, _listener: Listener, config: OutputConfigurationV1) -> None:
        logger.debug("Signal: output_manager test_event")
        self._output_manager_reconfigure(config, False)

    def _on_request_cursor(
        self, _listener: Listener, event: seat.PointerRequestSetCursorEvent
    ) -> None:
        if event._ptr.seat_client != self.seat.pointer_state._ptr.focused_client:
            # The request came from a cheeky window that doesn't have the pointer
            return

        self._cursor_state.surface = event.surface
        self._cursor_state.hotspot = event.hotspot

        if not self._cursor_state.hidden:
            self.cursor.set_surface(event.surface, event.hotspot)

    def _on_new_xdg_surface(self, _listener: Listener, xdg_surface: XdgSurface) -> None:
        assert self.qtile is not None
        logger.debug("Signal: xdg_shell new_surface_event")

        win: xdgwindow.XdgWindow | layer.LayerStatic

        if xdg_surface.role == XdgSurfaceRole.TOPLEVEL:
            # The new surface is a regular top-level window.
            win = xdgwindow.XdgWindow(self, self.qtile, xdg_surface)
            self.pending_windows.add(win)
            return

        if xdg_surface.role == XdgSurfaceRole.POPUP:
            # The new surface is a popup window.
            if not self._current_output:
                raise RuntimeError("Can't place a popup without any outputs enabled.")

            parent_surface = xdg_surface.popup.parent
            if parent_xdg_surface := XdgSurface.try_from_surface(parent_surface):
                # An XDG shell window or popup created this popup

                if parent_xdg_surface.role == XdgSurfaceRole.TOPLEVEL:
                    # If the immediate parent is a toplevel, we're a level 1 popup
                    win = cast(xdgwindow.XdgWindow, parent_xdg_surface.data)
                    tree = win.tree
                else:
                    # otherwise, this is a nested popup
                    tree = cast(SceneTree, parent_xdg_surface.data)
                    while parent_xdg_surface.role == XdgSurfaceRole.POPUP:
                        parent_xdg_surface = XdgSurface.try_from_surface(
                            parent_xdg_surface.popup.parent
                        )
                    win = cast(xdgwindow.XdgWindow, parent_xdg_surface.data)

                xdg_surface.data = self.scene.xdg_surface_create(tree, xdg_surface)

            elif parent := LayerSurfaceV1.try_from_wlr_surface(parent_surface):
                # A layer shell window created this popup
                win = cast(layer.LayerStatic, parent.data)
                self.scene.xdg_surface_create(win.popup_tree, xdg_surface)

            else:
                raise RuntimeError("Unknown surface as popup's parent.")

            # Position the popup
            box = xdg_surface.get_geometry()
            lx, ly = self.output_layout.closest_point(win.x + box.x, win.y + box.y)
            wlr_output = self.output_layout.output_at(lx, ly)
            screen_rect = wlr_output.data.get_screen_info()
            box = Box(screen_rect.x, screen_rect.y, screen_rect.width, screen_rect.height)
            box.x = round(box.x - lx)
            box.y = round(box.y - ly)
            xdg_surface.popup.unconstrain_from_box(box)
            return

        logger.warning("xdg_shell surface had no role set. Ignoring.")

    def _release_implicit_grab(self, time: int = 0) -> None:
        if self._implicit_grab is not None:
            logger.debug("Releasing implicit grab.")
            self._implicit_grab.finalize()
            self._implicit_grab = None
            # Pretend the cursor just appeared where it is.
            self._process_cursor_motion(time, self.cursor.x, self.cursor.y)

    def _create_implicit_grab(self, time: int, surface: Surface, sx: float, sy: float) -> None:
        self._release_implicit_grab(time)
        logger.debug("Creating implicit grab.")
        self._implicit_grab = ImplicitGrab(
            self, surface, self.cursor.x, self.cursor.y, int(sx), int(sy)
        )

    def _on_cursor_axis(self, _listener: Listener, event: pointer.PointerAxisEvent) -> None:
        handled = False

        if event.delta != 0 and not self.exclusive_client and not self._implicit_grab:
            # If we have a client who exclusively gets input, button bindings are disallowed.
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

    def _on_cursor_frame(self, _listener: Listener, _data: Any) -> None:
        self.seat.pointer_notify_frame()

    def _on_cursor_button(self, _listener: Listener, event: pointer.PointerButtonEvent) -> None:
        assert self.qtile is not None
        self.idle.notify_activity(self.seat)
        found = None
        pressed = event.button_state == input_device.ButtonState.PRESSED
        if pressed:
            self._pressed_button_count += 1
            if self._implicit_grab is None:
                found = self._focus_by_click()
        else:
            if self._pressed_button_count > 0:  # sanity check
                self._pressed_button_count -= 1

        if self._implicit_grab is not None:
            self.seat.pointer_notify_button(event.time_msec, event.button, event.button_state)
            if self._pressed_button_count == 0:
                self._release_implicit_grab(event.time_msec)
            return

        handled = False

        if not self.exclusive_client and event.button in wlrq.buttons:
            # If we have a client who exclusively gets input, button bindings are disallowed.
            button = wlrq.buttons.index(event.button) + 1
            handled = self._process_cursor_button(button, pressed)

        if not handled:
            if self._pressed_button_count == 1 and found and not self.live_dnd:
                win, surface, sx, sy = found
                if surface:
                    self._create_implicit_grab(event.time_msec, surface, sx, sy)
            self.seat.pointer_notify_button(event.time_msec, event.button, event.button_state)

    def _implicit_grab_motion(self, time: int) -> None:
        if self._implicit_grab:
            sx = self.cursor.x + self._implicit_grab.start_dx
            sy = self.cursor.y + self._implicit_grab.start_dy
            self.seat.pointer_notify_motion(time, sx, sy)

    def _on_cursor_motion(self, _listener: Listener, event: pointer.PointerMotionEvent) -> None:
        assert self.qtile is not None
        self.idle.notify_activity(self.seat)

        dx = event.delta_x
        dy = event.delta_y

        # Send relative pointer events to seat - used e.g. by games that have
        # constrained cursor movement but want movement events
        self._relative_pointer_manager_v1.send_relative_motion(
            self.seat,
            event.time_msec * 1000,
            dx,
            dy,
            event.unaccel_delta_x,
            event.unaccel_delta_y,
        )

        if self.active_pointer_constraint:
            if not self.active_pointer_constraint.rect.contains_point(
                self.cursor.x + dx, self.cursor.y + dy
            ):
                return

        self.cursor.move(dx, dy)

        if self._implicit_grab is None:
            self._process_cursor_motion(event.time_msec, self.cursor.x, self.cursor.y)
        else:
            self._implicit_grab_motion(event.time_msec)

    def _on_cursor_motion_absolute(
        self, _listener: Listener, event: pointer.PointerMotionAbsoluteEvent
    ) -> None:
        assert self.qtile is not None
        self.idle.notify_activity(self.seat)

        x, y = self.cursor.absolute_to_layout_coords(event.pointer.base, event.x, event.y)
        self.cursor.move(x - self.cursor.x, y - self.cursor.y)
        if self._implicit_grab is None:
            self._process_cursor_motion(event.time_msec, self.cursor.x, self.cursor.y)
        else:
            self._implicit_grab_motion(event.time_msec)

    def _on_cursor_pinch_begin(
        self,
        _listener: Listener,
        event: pointer.PointerPinchBeginEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_pinch_begin(self.seat, event.time_msec, event.fingers)

    def _on_cursor_pinch_update(
        self,
        _listener: Listener,
        event: pointer.PointerPinchUpdateEvent,
    ) -> None:
        self._gestures.send_pinch_update(
            self.seat, event.time_msec, event.dx, event.dy, event.scale, event.rotation
        )

    def _on_cursor_pinch_end(
        self,
        _listener: Listener,
        event: pointer.PointerPinchEndEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_pinch_end(self.seat, event.time_msec, event.cancelled)

    def _on_cursor_swipe_begin(
        self,
        _listener: Listener,
        event: pointer.PointerSwipeBeginEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_swipe_begin(self.seat, event.time_msec, event.fingers)

    def _on_cursor_swipe_update(
        self,
        _listener: Listener,
        event: pointer.PointerSwipeUpdateEvent,
    ) -> None:
        self._gestures.send_swipe_update(self.seat, event.time_msec, event.dx, event.dy)

    def _on_cursor_swipe_end(
        self,
        _listener: Listener,
        event: pointer.PointerSwipeEndEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_swipe_end(self.seat, event.time_msec, event.cancelled)

    def _on_cursor_hold_begin(
        self,
        _listener: Listener,
        event: pointer.PointerHoldBeginEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_hold_begin(self.seat, event.time_msec, event.fingers)

    def _on_cursor_hold_end(
        self,
        _listener: Listener,
        event: pointer.PointerHoldEndEvent,
    ) -> None:
        self.idle.notify_activity(self.seat)
        self._gestures.send_hold_end(self.seat, event.time_msec, event.cancelled)

    def _on_new_pointer_constraint(
        self, _listener: Listener, wlr_constraint: PointerConstraintV1
    ) -> None:
        logger.debug("Signal: pointer_constraints new_constraint")
        constraint = window.PointerConstraint(self, wlr_constraint)
        self.pointer_constraints.add(constraint)

        if self.seat.pointer_state.focused_surface == wlr_constraint.surface:
            if self.active_pointer_constraint:
                self.active_pointer_constraint.disable()
            constraint.enable()

    def _on_new_virtual_keyboard(
        self, _listener: Listener, virtual_keyboard: vkeyboard.VirtualKeyboardV1
    ) -> None:
        self._add_new_keyboard(virtual_keyboard.keyboard.base)

    def _on_new_virtual_pointer(
        self, _listener: Listener, new_pointer_event: vpointer.VirtualPointerV1NewPointerEvent
    ) -> None:
        device = self._add_new_pointer(new_pointer_event.new_pointer.pointer.base)
        logger.info("New virtual pointer: %s %s", *device.get_info())

    def _on_new_idle_inhibitor(
        self, _listener: Listener, idle_inhibitor: IdleInhibitorV1
    ) -> None:
        logger.debug("Signal: idle_inhibitor new_inhibitor")

        for win in self.qtile.windows_map.values():
            if isinstance(win, window.Window | window.Static):
                win.surface.for_each_surface(win.add_idle_inhibitor, idle_inhibitor)
                if idle_inhibitor.data:
                    # We break if the .data attribute was set, because that tells us
                    # that `win.add_idle_inhibitor` identified this inhibitor as
                    # belonging to that window.
                    break

    def _on_input_inhibitor_activate(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: input_inhibitor activate")
        assert self.qtile is not None
        self.exclusive_client = self._input_inhibit_manager.active_client

        # If another client has keyboard focus, unfocus it.
        if self.qtile.current_window and not self.qtile.current_window.belongs_to_client(
            self.exclusive_client
        ):
            self.focus_window(None)

        # If another client has pointer focus, unfocus that too.
        found = self._under_pointer()
        if found:
            win, _, _, _ = found

            # If we have a client who exclusively gets input, no other client's
            # surfaces are allowed to get pointer input.
            if isinstance(win, base.Internal) or not win.belongs_to_client(self.exclusive_client):
                self.cursor.set_xcursor(self._cursor_manager, "default")
                self.seat.pointer_notify_clear_focus()
                return

    def _on_input_inhibitor_deactivate(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: input_inhibitor deactivate")
        self.exclusive_client = None

    def _on_output_power_manager_set_mode(
        self, _listener: Listener, mode: OutputPowerV1SetModeEvent
    ) -> None:
        """
        Blank/unblank outputs via the output power management protocol.

        `_blanked_outputs` keeps track of those that were blanked because we don't want
        to unblank outputs that were already disabled due to not being part of the
        user-configured layout.
        """
        logger.debug("Signal: output_power_manager set_mode_event")
        wlr_output = mode.output
        output = cast(Output, wlr_output.data)

        if mode.mode == OutputPowerManagementV1Mode.ON:
            if output in self._blanked_outputs:
                wlr_output.enable(enable=True)
                try:
                    wlr_output.commit()
                except RuntimeError:
                    logger.warning("Couldn't enable output %s", wlr_output.name)
                    return
                self._blanked_outputs.remove(output)

        else:
            if wlr_output.enabled:
                wlr_output.enable(enable=False)
                try:
                    wlr_output.commit()
                except RuntimeError:
                    logger.warning("Couldn't disable output %s", wlr_output.name)
                    return
                self._blanked_outputs.add(output)

    def _on_new_layer_surface(self, _listener: Listener, layer_surface: LayerSurfaceV1) -> None:
        logger.debug("Signal: layer_shell new_surface_event")
        assert self.qtile is not None

        wid = self.new_wid()
        win = layer.LayerStatic(self, self.qtile, layer_surface, wid)
        logger.info("Managing new layer_shell window with window ID: %s", wid)
        self.qtile.manage(win)

    def _on_new_toplevel_decoration(
        self, _listener: Listener, decoration: xdg_decoration_v1.XdgToplevelDecorationV1
    ) -> None:
        logger.debug("Signal: xdg_decoration new_top_level_decoration")
        decoration.set_mode(xdg_decoration_v1.XdgToplevelDecorationV1Mode.SERVER_SIDE)

    def _on_xwayland_ready(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwayland ready")
        asyncio.get_running_loop().add_signal_handler(signal.SIGCHLD, reap_zombies)
        assert self._xwayland is not None
        self._xwayland.set_seat(self.seat)
        self.xwayland_atoms: dict[int, str] = wlrq.get_xwayland_atoms(self._xwayland)

        # Set the default XWayland cursor
        if xcursor := self._cursor_manager.get_xcursor("default"):
            image = next(xcursor.images, None)
            if image:
                self._xwayland.set_cursor(
                    image._ptr.buffer,
                    image._ptr.width * 4,
                    image._ptr.width,
                    image._ptr.height,
                    image._ptr.hotspot_x,
                    image._ptr.hotspot_y,
                )

    def _on_xwayland_new_surface(self, _listener: Listener, surface: xwayland.Surface) -> None:
        logger.debug("Signal: xwayland new_surface")
        assert self.qtile is not None
        win = xwindow.XWindow(self, self.qtile, surface)
        self.pending_windows.add(win)

    def _on_xdg_activation_v1_request_activate(
        self, _listener: Listener, event: xdg_activation_v1.XdgActivationV1RequestActivateEvent
    ) -> None:
        """Respond to window activate events via the XDG activation V1 protocol."""
        logger.debug("Signal: xdg_activation_v1 request_activate")
        assert self.qtile is not None

        focus_on_window_activation = self.qtile.config.focus_on_window_activation
        if focus_on_window_activation == "never":
            logger.debug("Ignoring focus request (focus_on_window_activation='never')")
            return

        surface = event.surface
        if surface:
            xdg_surface = XdgSurface.try_from_surface(surface)
            if xdg_surface is not None:
                if win := xdg_surface.data:
                    win.handle_activation_request(focus_on_window_activation)
                else:
                    # Shouldn't happen.
                    logger.debug("Failed to find window to activate. Ignoring request.")

    def _output_manager_reconfigure(self, config: OutputConfigurationV1, apply: bool) -> None:
        """
        See if an output configuration would be accepted by the backend, and apply it if
        desired.
        """
        ok = True

        for head in config.heads:
            head_state = head.state
            wlr_output = head_state.output

            state = OutputState()
            state.set_enabled(head_state.enabled)

            if head_state.enabled:
                if head_state.mode:
                    state.set_mode(head_state.mode)
                else:
                    state.set_custom_mode(head_state.custom_mode)

                state.set_transform(head_state.transform)
                state.set_scale(head_state.scale)
                state.set_adaptive_sync_enabled(head_state.adaptive_sync_enabled)
                # Rescale the cursor if necessary
                box = self.output_layout.get_box(wlr_output)
                if box.x != head_state.x or box.y != head_state.y:
                    self.output_layout.add(wlr_output, head_state.x, head_state.y)
                # Ensure we have cursors loaded for the new scale factor.
                self._cursor_manager.load(head_state.scale)
                if not self.seat.pointer_state.focused_surface:
                    self.cursor.set_xcursor(self._cursor_manager, "default")

            if apply:
                ok = ok and wlr_output.commit(state)
            else:
                ok = ok and wlr_output.test(state)
            state.finish()

        if ok:
            config.send_succeeded()
        else:
            config.send_failed()
        config.destroy()
        if apply:
            self._on_output_layout_change()

    def _process_cursor_motion(self, time_msec: int, cx: float, cy: float) -> None:
        assert self.qtile
        cx_int = int(cx)
        cy_int = int(cy)

        if not self.exclusive_client:
            # If we have a client who exclusively gets input, button bindings are
            # disallowed, so process_button_motion doesn't need to be updated.
            self.qtile.process_button_motion(cx_int, cy_int)

        if len(self.get_enabled_outputs()) > 1:
            current_wlr_output = self.output_layout.output_at(cx, cy)
            if current_wlr_output:
                current_output = current_wlr_output.data
                if self._current_output is not current_output:
                    self._current_output = current_output

        if self.live_dnd:
            self.live_dnd.position(cx, cy)

        self._focus_pointer(cx_int, cy_int, motion=time_msec)

    def _focus_pointer(self, cx: int, cy: int, motion: int | None = None) -> None:
        assert self.qtile is not None
        found = self._under_pointer()

        if found:
            win, surface, sx, sy = found

            if self.exclusive_client:
                # If we have a client who exclusively gets input, no other client's
                # surfaces are allowed to get pointer input.
                if isinstance(win, base.Internal) or not win.belongs_to_client(
                    self.exclusive_client
                ):
                    # Moved to an internal or unrelated window
                    if self._hovered_window is not win:
                        logger.debug(
                            "Pointer focus withheld from window not owned by exclusive client."
                        )
                        self.cursor.set_xcursor(self._cursor_manager, "default")
                        self.seat.pointer_notify_clear_focus()
                        self._hovered_window = win
                    return

            if isinstance(win, window.Internal):
                if self._hovered_window is win:
                    # pointer remained within the same Internal window
                    if motion is not None:
                        win.process_pointer_motion(
                            cx - self._hovered_window.x,
                            cy - self._hovered_window.y,
                        )
                else:
                    if self._hovered_window:
                        if isinstance(self._hovered_window, window.Internal):
                            if motion is not None:
                                # moved from an Internal to a different Internal
                                self._hovered_window.process_pointer_leave(
                                    cx - self._hovered_window.x,
                                    cy - self._hovered_window.y,
                                )
                        elif self.seat.pointer_state.focused_surface:
                            # moved from a Window or Static to an Internal
                            self.cursor.set_xcursor(self._cursor_manager, "default")
                            self.seat.pointer_notify_clear_focus()
                    win.process_pointer_enter(cx, cy)
                    self._hovered_window = win
                return

            if surface:
                # The pointer is in a client's surface
                self.seat.pointer_notify_enter(surface, sx, sy)
                if motion is not None:
                    self.seat.pointer_notify_motion(motion, sx, sy)
            else:
                # The pointer is on the border of a client's window
                if self.seat.pointer_state.focused_surface:
                    # We just moved out of a client's surface
                    self.cursor.set_xcursor(self._cursor_manager, "default")
                    self.seat.pointer_notify_clear_focus()

            if self._hovered_window is not win:
                # We only want to fire client_mouse_enter once, so check
                # self._hovered_window.
                hook.fire("client_mouse_enter", win)

            if win is not self.qtile.current_window:
                if motion is not None and self.qtile.config.follow_mouse_focus is True:
                    if isinstance(win, window.Static):
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

        else:
            # There is no window under the pointer
            if self._hovered_window:
                if isinstance(self._hovered_window, window.Internal):
                    # We just moved out of an Internal
                    self._hovered_window.process_pointer_leave(
                        cx - self._hovered_window.x,
                        cy - self._hovered_window.y,
                    )
                else:
                    # We just moved out of a Window or Static
                    self.cursor.set_xcursor(self._cursor_manager, "default")
                    self.seat.pointer_notify_clear_focus()
                self._hovered_window = None

    def _process_cursor_button(self, button: int, pressed: bool) -> bool:
        assert self.qtile is not None
        handled = False

        if pressed:
            if keyboard := self.seat.get_keyboard():
                handled = self.qtile.process_button_click(
                    button, keyboard.modifier, int(self.cursor.x), int(self.cursor.y)
                )
            else:
                logger.warning("No active keyboard found, keybinding may be missed.")

            if isinstance(self._hovered_window, window.Internal):
                self._hovered_window.process_button_click(
                    int(self.cursor.x - self._hovered_window.x),
                    int(self.cursor.y - self._hovered_window.y),
                    button,
                )
        else:
            if keyboard := self.seat.get_keyboard():
                handled = self.qtile.process_button_release(button, keyboard.modifier)
            else:
                logger.warning("No active keyboard found, keybinding may be missed.")

            if isinstance(self._hovered_window, window.Internal):
                self._hovered_window.process_button_release(
                    int(self.cursor.x - self._hovered_window.x),
                    int(self.cursor.y - self._hovered_window.y),
                    button,
                )

        return handled

    def _add_new_pointer(self, wlr_device: input_device.InputDevice) -> inputs.Pointer:
        device = inputs.Pointer(self, wlr_device)
        self._pointers.append(device)
        self.cursor.attach_input_device(wlr_device)
        self.cursor.set_xcursor(self._cursor_manager, "default")

        # Map input device to output if required.
        if output_name := pointer.Pointer.from_input_device(wlr_device).output_name:
            target_output = None
            for output in self.get_enabled_outputs():
                if output_name == output.wlr_output.name:
                    target_output = output.wlr_output
                    break

            if target_output:
                logger.debug("Mapping pointer to output: %s", output_name)
            else:
                logger.warning("Failed to find output (%s) for mapping pointer.", output_name)
            self.cursor.map_input_to_output(wlr_device, target_output)

        return device

    def _add_new_keyboard(self, wlr_device: input_device.InputDevice) -> inputs.Keyboard:
        keyboard = Keyboard.from_input_device(wlr_device)
        device = inputs.Keyboard(self, wlr_device, keyboard)
        self.keyboards.append(device)
        self.seat.set_keyboard(keyboard)
        return device

    def _configure_pending_inputs(self) -> None:
        """Configure inputs that were detected before the config was loaded."""
        assert self.qtile is not None

        if self.qtile.config.wl_input_rules:
            for device in self._pending_input_devices:
                device.configure(self.qtile.config.wl_input_rules)
        self._pending_input_devices.clear()

    def setup_listener(self) -> None:
        """Setup a listener for the given qtile instance"""
        logger.debug("Adding io watch")
        # destroy the old one and load a new one with config settings
        self._cursor_manager.destroy()
        self._cursor_manager = XCursorManager(
            self.qtile.config.wl_xcursor_theme, self.qtile.config.wl_xcursor_size
        )
        self.cursor.set_xcursor(self._cursor_manager, "default")
        self.fd = lib.wl_event_loop_get_fd(self.event_loop._ptr)
        if self.fd:
            asyncio.get_running_loop().add_reader(self.fd, self._poll)
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
        if not self.display.destroyed:
            self.display.flush_clients()
            self.event_loop.dispatch(0)
            self.display.flush_clients()

    def on_config_load(self, initial: bool) -> None:
        if initial:
            # This backend does not support restarting
            return

        assert self.qtile is not None

        managed_wins = [
            w for w in self.qtile.windows_map.values() if isinstance(w, window.Window)
        ]
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
            for device in [*self.keyboards, *self._pointers]:
                device.configure(self.qtile.config.wl_input_rules)

    def new_wid(self) -> int:
        """Get a new unique window ID"""
        assert self.qtile is not None
        return max(self.qtile.windows_map.keys(), default=0) + 1

    def focus_window(
        self, win: window.WindowType | None, surface: Surface | None = None, enter: bool = True
    ) -> None:
        if self.seat.destroyed:
            return

        if self.exclusive_client:
            # If we have a client who exclusively gets input, no other client's surfaces
            # are allowed to get keyboard input.
            if not win:
                self.seat.keyboard_clear_focus()
                return
            if isinstance(win, base.Internal) or not win.belongs_to_client(self.exclusive_client):
                logger.debug("Keyboard focus withheld from window not owned by exclusive client.")
                # We can't focus surfaces belonging to other clients.
                return

        if self.exclusive_layer and win is not self.exclusive_layer:
            logger.debug("Keyboard focus withheld: focus is fixed to exclusive layer surface.")
            return

        if isinstance(win, base.Internal):
            self.focused_internal = win
            self.seat.keyboard_clear_focus()
            return

        if surface is None and win is not None:
            surface = win.surface.surface

        if self.focused_internal:
            self.focused_internal = None

        if isinstance(win, layer.LayerStatic):
            if not win.surface.current.keyboard_interactive:
                return

        if isinstance(win, xwindow.XStatic):
            if win.surface.override_redirect and not win.surface.or_surface_wants_focus():
                return
            if win.surface.icccm_input_model() == xwayland.ICCCMInputModel.NONE:
                return

        previous_surface = self.seat.keyboard_state.focused_surface
        if previous_surface == surface:
            return

        if previous_surface is not None:
            # Deactivate the previously focused surface
            if previous_xdg_surface := XdgSurface.try_from_surface(previous_surface):
                if not win or win.surface != previous_xdg_surface:
                    previous_xdg_surface.set_activated(False)
                    if prev_win := previous_xdg_surface.data:
                        if ftm_handle := prev_win.ftm_handle:
                            ftm_handle.set_activated(False)

            else:
                prev_xwayland_surface = xwayland.Surface.try_from_wlr_surface(previous_surface)
                if prev_xwayland_surface is not None and (
                    not win or win.surface != prev_xwayland_surface
                ):
                    prev_xwayland_surface.activate(False)
                    if prev_win := prev_xwayland_surface.data:
                        if ftm_handle := prev_win.ftm_handle:
                            ftm_handle.set_activated(False)

        if not win or not surface:
            self.seat.keyboard_clear_focus()
            return

        logger.debug("Focusing new window")
        ftm_handle = None

        if isinstance(win.surface, XdgSurface):
            win.surface.set_activated(True)
            ftm_handle = win.ftm_handle

        elif isinstance(win.surface, xwayland.Surface):
            win.surface.activate(True)
            ftm_handle = win.ftm_handle

        if ftm_handle:
            ftm_handle.set_activated(True)

        if enter:
            if keyboard := self.seat.get_keyboard():
                self.seat.keyboard_notify_enter(surface, keyboard)

    def _focus_by_click(self) -> tuple[window.WindowType, Surface | None, float, float] | None:
        assert self.qtile is not None
        found = self._under_pointer()

        if found:
            win, surface, sx, sy = found

            if self.exclusive_client:
                # If we have a client who exclusively gets input, no other client's
                # surfaces are allowed to get focus.
                if isinstance(win, base.Internal) or not win.belongs_to_client(
                    self.exclusive_client
                ):
                    logger.debug("Focus withheld from window not owned by exclusive client.")
                    return None

            if self.qtile.config.bring_front_click is True:
                win.bring_to_front()
            elif self.qtile.config.bring_front_click == "floating_only":
                if isinstance(win, base.Window) and win.floating:
                    win.bring_to_front()

            if isinstance(win, window.Static):
                if win.screen is not self.qtile.current_screen:
                    self.qtile.focus_screen(win.screen.index, warp=False)
                win.focus(False)
            elif isinstance(win, window.Window):
                if win.group and win.group.screen is not self.qtile.current_screen:
                    self.qtile.focus_screen(win.group.screen.index, warp=False)
                self.qtile.current_group.focus(win, False)

        else:
            screen = self.qtile.find_screen(int(self.cursor.x), int(self.cursor.y))
            if screen:
                self.qtile.focus_screen(screen.index, warp=False)

        return found

    def _under_pointer(self) -> tuple[window.WindowType, Surface | None, float, float] | None:
        """
        Find which window and surface is currently under the pointer, if any.
        """
        # Warning: this method is a bit difficult to follow and has liberal use of
        # typing.cast. Make sure you're familiar with how the scene-graph tree is laid
        # out (see diagram in __init__ above).
        assert self.qtile is not None

        maybe_node = self.windows_tree.node.node_at(self.cursor.x, self.cursor.y)
        if maybe_node is None:
            # We didn't find any node, so there is no window under the pointer.
            return None

        node, sx, sy = maybe_node

        if node.type == SceneNodeType.BUFFER:
            # Buffer nodes can be any surface or subsurface (nested in subtrees) of a
            # client or Internal window. In all cases we will get a wlr_scene_buffer,
            # but only client surfaces will have a wlr_scene_surface.
            scene_buffer = cast(SceneBuffer, SceneBuffer.from_node(node))

            if scene_surface := SceneSurface.from_buffer(scene_buffer):
                # We got a node that is part of a window, walk up the scene graph to
                # find the window object. It could also be an XDG popup, which can be
                # the child of either an XDG window or a layer shell window.
                win = self.win_from_node(node)
                return win, scene_surface.surface, sx, sy

            # We didn't get a wlr_scene_surface, so we're dealing with an internal window
            # Internal windows have a scenetree for borders. The parent's data we will use to cast to an internal window
            parent_tree = cast(SceneTree, node.parent)
            win = cast(window.Internal, parent_tree.node.data)
            return win, None, sx, sy

        if node.type == SceneNodeType.RECT:
            # Rect nodes are only used for window borders. Their immediate parent is the
            # window container, which gives us the window at .data.
            # We have to differentiate between internal windows and normal windows
            parent_tree = cast(SceneTree, node.parent)
            if isinstance(parent_tree.node.data, window.Internal):
                win = cast(window.Internal, parent_tree.node.data)
            else:
                win = cast(window.Window, parent_tree.node.data)
            return win, None, sx, sy

        logger.warning("Couldn't determine what was under the pointer. Please report.")
        return None

    def check_idle_inhibitor(self) -> None:
        """
        Checks if any window that is currently mapped has idle inhibitor
        and if so inhibits idle
        """
        assert self.qtile is not None

        for win in self.qtile.windows_map.values():
            if not isinstance(win, window.Internal) and win.is_idle_inhibited:
                # TODO: do we also need to check that the window is mapped?
                self.idle.set_inhibited(True)
                return

        self.idle.set_inhibited(False)

    def get_screen_info(self) -> list[ScreenRect]:
        """Get the output information"""
        return [output.get_screen_info() for output in self.get_enabled_outputs()]

    def _get_sym_from_code(self, keycode: int) -> str:
        keyboard = self.active_keyboard
        if keyboard is None:
            raise QtileError("Unable to grab keycode. No active keyboard found.")
        return keyboard._state.key_get_one_sym(keycode)

    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Configure the backend to grab the key event"""
        if isinstance(key.key, str):
            keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = wlrq.translate_masks(key.modifiers)
        self.grabbed_keys.append((keysym, mask_key))
        return keysym, mask_key

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Release the given key event"""
        if isinstance(key.key, str):
            keysym = xkb.keysym_from_name(key.key, case_insensitive=True)
        else:
            keysym = self._get_sym_from_code(key.key)
        mask_key = wlrq.translate_masks(key.modifiers)
        self.grabbed_keys.remove((keysym, mask_key))
        return keysym, mask_key

    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""
        self.grabbed_keys.clear()

    def grab_button(self, mouse: config.Mouse) -> int:
        """Configure the backend to grab the mouse event"""
        return wlrq.translate_masks(mouse.modifiers)

    def warp_pointer(self, x: float, y: float) -> None:
        """Warp the pointer to the coordinates in relative to the output layout"""
        self.cursor.warp(WarpMode.LayoutClosest, x, y)

    @contextlib.contextmanager
    def masked(self) -> Generator:
        yield
        self._focus_pointer(int(self.cursor.x), int(self.cursor.y))

    def flush(self) -> None:
        self._poll()

    def create_internal(self, x: int, y: int, width: int, height: int) -> base.Internal:
        assert self.qtile is not None
        internal = window.Internal(self, self.qtile, x, y, width, height)
        self.qtile.manage(internal)
        return internal

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

    @property
    def painter(self) -> Any:
        return wlrq.Painter(self)

    def remove_output(self, output: Output) -> None:
        # already removed
        if output not in self._outputs:
            return
        self._outputs.remove(output)
        box = self.output_layout.get_box(output.wlr_output)
        if not lib.wlr_box_empty(box._ptr):
            self.output_layout.remove(output.wlr_output)
        if output is self._current_output:
            en_outputs = self.get_enabled_outputs()
            self._current_output = en_outputs[0] if en_outputs else None

    def remove_pointer_constraints(self, window: window.Window | window.Static) -> None:
        for pc in self.pointer_constraints.copy():
            if pc.window is window:
                pc.finalize()

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        return xkb.keysym_from_name(name, case_insensitive=True)

    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        """Simulates a keypress on the focused window."""
        keysym = xkb.keysym_from_name(key, case_insensitive=True)
        mods = wlrq.translate_masks(modifiers)

        if (keysym, mods) in self.grabbed_keys:
            assert self.qtile is not None
            self.qtile.process_key_event(keysym, mods)
            return

        if self.focused_internal:
            self.focused_internal.process_key_press(keysym)

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
        if self.keyboards:
            for keyboard in self.keyboards:
                keyboard.set_keymap(layout, options, variant)
        else:
            logger.warning("Could not set keymap: no keyboards set up.")

    @expose_command()
    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal to that specified"""
        success = self.backend.get_session().change_vt(vt)
        if not success:
            logger.warning("Could not change VT to: %s", vt)
        return success

    @expose_command()
    def hide_cursor(self) -> None:
        """Hide the cursor."""
        if not self._cursor_state.hidden:
            self.cursor.set_surface(None, self._cursor_state.hotspot)
            self._cursor_state.hidden = True

    @expose_command()
    def unhide_cursor(self) -> None:
        """Unhide the cursor."""
        if self._cursor_state.hidden:
            self.cursor.set_surface(
                self._cursor_state.surface,
                self._cursor_state.hotspot,
            )
            self._cursor_state.hidden = False

    @expose_command()
    def get_inputs(self) -> dict[str, list[dict[str, str]]]:
        """Get information on all input devices."""
        info: defaultdict[str, list[dict]] = defaultdict(list)
        devices: list[inputs._Device] = self.keyboards + self._pointers  # type: ignore

        for dev in devices:
            type_key, identifier = dev.get_info()
            type_info = dict(
                name=dev.wlr_device.name,
                identifier=identifier,
            )
            info[type_key].append(type_info)

        return dict(info)

    @expose_command()
    def query_tree(self) -> list[int]:
        """Get IDs of all mapped windows in ascending Z order."""
        wids = []

        def iterator(buffer: SceneBuffer, _sx: int, _sy: int, _data: None) -> None:
            # Walk back up tree until we find a window or run out of parents
            node = buffer.node
            while True:
                if win := node.data:
                    if node.enabled:
                        # TODO does this need to check the container node rather than
                        # three node within it?
                        wids.append(win.wid)
                    return
                parent = node.parent
                if not parent:
                    return
                node = parent.node

        self.scene.tree.node.for_each_buffer(iterator, None)
        return wids

    def get_mouse_position(self) -> tuple[int, int]:
        """Get mouse coordinates."""
        return int(self.cursor.x), int(self.cursor.y)

    @property
    def hovered_window(self) -> base.WindowType | None:
        return self._hovered_window
