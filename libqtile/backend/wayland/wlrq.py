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

import functools
import operator
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import cairocffi
from pywayland.server import Listener
from wlroots import ffi as wlr_ffi
from wlroots import lib as wlr_lib
from wlroots.wlr_types import Buffer, SceneBuffer, SceneTree, data_device_manager
from wlroots.wlr_types.keyboard import KeyboardModifier
from wlroots.wlr_types.scene import SceneRect

from libqtile.log_utils import logger
from libqtile.utils import QtileError, rgb

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    pass

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pywayland.server import Signal
    from wlroots import xwayland
    from wlroots.wlr_types import Surface

    from libqtile.backend.wayland.core import Core
    from libqtile.config import Screen
    from libqtile.utils import ColorType


class WlrQError(QtileError):
    pass


ModMasks = {
    "shift": KeyboardModifier.SHIFT,
    "lock": KeyboardModifier.CAPS,
    "control": KeyboardModifier.CTRL,
    "mod1": KeyboardModifier.ALT,
    "mod2": KeyboardModifier.MOD2,
    "mod3": KeyboardModifier.MOD3,
    "mod4": KeyboardModifier.LOGO,
    "mod5": KeyboardModifier.MOD5,
}

# from linux/input-event-codes.h
_KEY_MAX = 0x2FF
# These are mouse buttons 1-9
BTN_LEFT = 0x110
BTN_MIDDLE = 0x112
BTN_RIGHT = 0x111
SCROLL_UP = _KEY_MAX + 1
SCROLL_DOWN = _KEY_MAX + 2
SCROLL_LEFT = _KEY_MAX + 3
SCROLL_RIGHT = _KEY_MAX + 4
BTN_SIDE = 0x113
BTN_EXTRA = 0x114

buttons = [
    BTN_LEFT,
    BTN_MIDDLE,
    BTN_RIGHT,
    SCROLL_UP,
    SCROLL_DOWN,
    SCROLL_LEFT,
    SCROLL_RIGHT,
    BTN_SIDE,
    BTN_EXTRA,
]

# from drm_fourcc.h
DRM_FORMAT_ARGB8888 = 875713089


def translate_masks(modifiers: list[str]) -> int:
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(ModMasks[i.lower()])
        except KeyError as e:
            raise WlrQError(f"Unknown modifier: {i}") from e
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


class Painter:
    def __init__(self, core: Core):
        self.core = core

    def _clear_previous_background(self, screen: Screen) -> None:
        # Drop references to existing wallpaper if there is one
        if screen in self.core.wallpapers:
            old_scene_buffer, old_surface = self.core.wallpapers.pop(screen)
            old_scene_buffer.node.destroy()
            if old_surface is not None:
                old_surface.finish()

    def fill(self, screen: Screen, background: ColorType) -> None:
        self._clear_previous_background(screen)
        rect = SceneRect(self.core.wallpaper_tree, screen.width, screen.height, rgb(background))
        self.core.wallpapers[screen] = (rect, None)

    def paint(self, screen: Screen, image_path: str, mode: str | None = None) -> None:
        try:
            with open(image_path, "rb") as f:
                image, _ = cairocffi.pixbuf.decode_to_image_surface(f.read())
        except OSError:
            logger.exception("Could not load wallpaper:")
            return

        image_w = image.get_width()
        image_h = image.get_height()

        # the dimensions of cairo are the full screen if the mode is not specified
        # otherwise they are the image dimensions for fill and stretch mode
        # the actual scaling of the image is then done with wlroots functions
        # so that the GPU is used
        cairo_w = image_w if mode in ["fill", "stretch"] else screen.width
        cairo_h = image_h if mode in ["fill", "stretch"] else screen.height
        surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, cairo_w, cairo_h)
        with cairocffi.Context(surface) as context:
            context.save()
            context.set_operator(cairocffi.OPERATOR_SOURCE)
            context.set_source_rgb(0, 0, 0)
            context.rectangle(0, 0, cairo_w, cairo_h)
            context.fill()
            context.restore()
            context.set_source_surface(image)
            context.paint()
        surface.flush()
        stride = surface.get_stride()
        data = cairocffi.cairo.cairo_image_surface_get_data(surface._pointer)
        wlr_buffer = lib.cairo_buffer_create(cairo_w, cairo_h, stride, data)
        if wlr_buffer == ffi.NULL:
            raise RuntimeError("Couldn't allocate cairo buffer.")

        self._clear_previous_background(screen)

        # We need to keep a reference to the surface so its data persists
        if scene_buffer := SceneBuffer.create(self.core.wallpaper_tree, Buffer(wlr_buffer)):
            scene_buffer.node.set_position(screen.x, screen.y)
            self.core.wallpapers[screen] = (scene_buffer, surface)
        else:
            logger.warning("Failed to create wlr_scene_buffer.")
            return

        # Handle fill mode
        if mode == "fill":
            if image_w / image_h > screen.width / screen.height:
                # image is wider than screen; clip left and right
                new_w = image_h * screen.width / screen.height
                side = (image_w - new_w) // 2
                fbox = wlr_ffi.new("struct wlr_fbox *")
                fbox.x = side
                fbox.y = 0
                fbox.width = image_w - 2 * side
                fbox.height = image_h
                wlr_lib.wlr_scene_buffer_set_source_box(scene_buffer._ptr, fbox)
            elif image_w / image_h < screen.width / screen.height:
                # image is taller than screen; clip top and bottom
                new_h = image_w * screen.height / screen.width
                side = (image_h - new_h) // 2
                fbox = wlr_ffi.new("struct wlr_fbox *")
                fbox.x = 0
                fbox.y = side
                fbox.width = image_w
                fbox.height = image_h - 2 * side
                wlr_lib.wlr_scene_buffer_set_source_box(scene_buffer._ptr, fbox)
            wlr_lib.wlr_scene_buffer_set_dest_size(scene_buffer._ptr, screen.width, screen.height)
        elif mode == "stretch":
            wlr_lib.wlr_scene_buffer_set_dest_size(scene_buffer._ptr, screen.width, screen.height)
        elif mode == "center":
            target_x = (screen.width - image.get_width()) // 2
            target_y = (screen.height - image.get_height()) // 2
            scene_buffer.node.set_position(target_x, target_y)
        # Otherwise (mode is None), the image takes up its native size in
        # layout coordinate pixels (which doesn't account for output scaling)


class HasListeners:
    """
    Classes can subclass this to get some convenience handlers around
    `pywayland.server.Listener`.

    This guarantees that all listeners that set up and then removed in reverse order.
    """

    def add_listener(self, event: Signal, callback: Callable) -> None:
        if not hasattr(self, "_listeners"):
            self._listeners = []
        listener = Listener(callback)
        event.add(listener)
        self._listeners.append(listener)

    def finalize_listeners(self) -> None:
        for listener in reversed(self._listeners):
            listener.remove()
        self._listeners.clear()

    def finalize_listener(self, event: Signal) -> None:
        for listener in self._listeners.copy():
            if listener._signal._ptr == event._ptr:
                listener.remove()
                return
        logger.warning("Failed to remove listener for event: %s", event)


class Dnd(HasListeners):
    """A helper for drag and drop functionality."""

    def __init__(self, core: Core, wlr_drag: data_device_manager.Drag):
        self.core = core
        self.icon = cast(data_device_manager.DragIcon, wlr_drag.icon)
        self.add_listener(self.icon.destroy_event, self._on_destroy)
        self.node = SceneTree.drag_icon_create(core.drag_icon_tree, self.icon).node

        # The data handle at .data is used for finding what's under the cursor when it's
        # moved.
        self.data_handle = ffi.new_handle(self)
        self.node.data = self.data_handle

    def finalize(self) -> None:
        self.finalize_listeners()
        self.core.live_dnd = None
        self.node.destroy()
        self.node.data = None
        self.data_handle = None

    def _on_destroy(self, _listener: Listener, _event: Any) -> None:
        logger.debug("Signal: wlr_drag destroy")
        self.finalize()

    def position(self, cx: float, cy: float) -> None:
        self.node.set_position(int(cx), int(cy))


def get_xwayland_atoms(xwayland: xwayland.XWayland) -> dict[int, str]:
    """
    These can be used when matching on XWayland clients with wm_type.
    http://standards.freedesktop.org/wm-spec/latest/ar01s05.html#idm139870830002400
    """
    xwayland_wm_types = {
        "_NET_WM_WINDOW_TYPE_DESKTOP": "desktop",
        "_NET_WM_WINDOW_TYPE_DOCK": "dock",
        "_NET_WM_WINDOW_TYPE_TOOLBAR": "toolbar",
        "_NET_WM_WINDOW_TYPE_MENU": "menu",
        "_NET_WM_WINDOW_TYPE_UTILITY": "utility",
        "_NET_WM_WINDOW_TYPE_SPLASH": "splash",
        "_NET_WM_WINDOW_TYPE_DIALOG": "dialog",
        "_NET_WM_WINDOW_TYPE_DROPDOWN_MENU": "dropdown",
        "_NET_WM_WINDOW_TYPE_POPUP_MENU": "menu",
        "_NET_WM_WINDOW_TYPE_TOOLTIP": "tooltip",
        "_NET_WM_WINDOW_TYPE_NOTIFICATION": "notification",
        "_NET_WM_WINDOW_TYPE_COMBO": "combo",
        "_NET_WM_WINDOW_TYPE_DND": "dnd",
        "_NET_WM_WINDOW_TYPE_NORMAL": "normal",
    }

    atoms = {}
    for atom, name in xwayland_wm_types.items():
        atoms[xwayland.get_atom(atom)] = name

    return atoms


@dataclass()
class CursorState:
    """
    The surface and hotspot state of the cursor. This is tracked directly by the core so
    that the cursor can be hidden and later restored to this state at will.
    """

    surface: Surface | None = None
    hotspot: tuple[int, int] = (0, 0)
    hidden: bool = False
