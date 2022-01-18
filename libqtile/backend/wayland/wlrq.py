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
from typing import TYPE_CHECKING

import cairocffi
from pywayland.server import Listener
from wlroots.wlr_types import Texture
from wlroots.wlr_types.keyboard import KeyboardModifier
from wlroots.wlr_types.pointer_constraints_v1 import (
    PointerConstraintV1,
    PointerConstraintV1StateField,
)
from wlroots.wlr_types.xdg_shell import XdgSurface

from libqtile.backend.base import Internal
from libqtile.log_utils import logger
from libqtile.utils import QtileError

if TYPE_CHECKING:
    from typing import Callable, Dict, List, Optional, Set

    from pywayland.server import Signal
    from wlroots import xwayland
    from wlroots.wlr_types import Box, data_device_manager

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.output import Output
    from libqtile.backend.wayland.window import WindowType


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


def translate_masks(modifiers: List[str]) -> int:
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(ModMasks[i])
        except KeyError as e:
            raise WlrQError("Unknown modifier: %s" % i) from e
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


class Painter:
    def __init__(self, core):
        self.core = core

    def paint(self, screen, image_path, mode=None):
        try:
            with open(image_path, "rb") as f:
                image, _ = cairocffi.pixbuf.decode_to_image_surface(f.read())
        except IOError as e:
            logger.error("Wallpaper: %s" % e)
            return

        surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, screen.width, screen.height)
        with cairocffi.Context(surface) as context:
            if mode == "fill":
                context.rectangle(0, 0, screen.width, screen.height)
                context.clip()
                image_w = image.get_width()
                image_h = image.get_height()
                width_ratio = screen.width / image_w
                if width_ratio * image_h >= screen.height:
                    context.scale(width_ratio)
                else:
                    height_ratio = screen.height / image_h
                    context.translate(-(image_w * height_ratio - screen.width) // 2, 0)
                    context.scale(height_ratio)
            elif mode == "stretch":
                context.scale(
                    sx=screen.width / image.get_width(),
                    sy=screen.height / image.get_height(),
                )
            context.set_source_surface(image)
            context.paint()

            stride = surface.format_stride_for_width(cairocffi.FORMAT_ARGB32, screen.width)
            surface.flush()
            texture = Texture.from_pixels(
                self.core.renderer,
                DRM_FORMAT_ARGB8888,
                stride,
                screen.width,
                screen.height,
                cairocffi.cairo.cairo_image_surface_get_data(surface._pointer),
            )
            outputs = [output for output in self.core.outputs if output.wlr_output.enabled]
            outputs[screen.index].wallpaper = texture


class HasListeners:
    """
    Classes can subclass this to get some convenience handlers around
    `pywayland.server.Listener`.

    This guarantees that all listeners that set up and then removed in reverse order.
    """

    def add_listener(self, event: Signal, callback: Callable):
        if not hasattr(self, "_listeners"):
            self._listeners = []
        listener = Listener(callback)
        event.add(listener)
        self._listeners.append(listener)

    def finalize_listeners(self):
        for listener in reversed(self._listeners):
            listener.remove()


class PointerConstraint(HasListeners):
    """
    A small object to listen to signals on `struct wlr_pointer_constraint_v1` instances.
    """

    rect: Box

    def __init__(self, core: Core, wlr_constraint: PointerConstraintV1):
        self.core = core
        self.wlr_constraint = wlr_constraint
        self.window: Optional[WindowType] = None
        self._warp_target = (0, 0)
        self._needs_warp = False

        self.add_listener(wlr_constraint.set_region_event, self._on_set_region)
        self.add_listener(wlr_constraint.destroy_event, self._on_destroy)

        self._get_window()

    def _get_window(self):
        for win in self.core.qtile.windows_map.values():
            if not isinstance(win, Internal) and isinstance(win.surface, XdgSurface):
                if win.surface.surface == self.wlr_constraint.surface:
                    break
        else:
            self.finalize()

        self.window = win

    def finalize(self):
        if self.core.active_pointer_constraint is self:
            self.disable()
        self.finalize_listeners()
        self.core.pointer_constraints.remove(self)

    def _on_set_region(self, _listener, _data):
        logger.debug("Signal: wlr_pointer_constraint_v1 set_region")
        self._get_region()

    def _on_destroy(self, _listener, wlr_constraint: PointerConstraintV1):
        logger.debug("Signal: wlr_pointer_constraint_v1 destroy")
        self.finalize()

    def _on_commit(self, _listener, _data):
        if self._needs_warp:
            # Warp in case the pointer is not inside the rect
            if not self.rect.contains_point(self.cursor.x, self.cursor.y):
                self.core.warp_pointer(*self._warp_target)
            self._needs_warp = False

    def _get_region(self):
        rect = self.wlr_constraint.region.rectangles_as_boxes()[0]
        rect.x += self.window.x + self.window.borderwidth
        rect.y += self.window.y + self.window.borderwidth
        self._warp_target = (rect.x + rect.width / 2, rect.y + rect.height / 2)
        self.rect = rect
        self._needs_warp = True

    def enable(self):
        logger.debug("Enabling pointer constraints.")
        self.core.active_pointer_constraint = self
        self._get_region()
        self.add_listener(self.wlr_constraint.surface.commit_event, self._on_commit)
        self.wlr_constraint.send_activated()

    def disable(self):
        logger.debug("Disabling pointer constraints.")

        if self.wlr_constraint.current.committed & PointerConstraintV1StateField.CURSOR_HINT:
            x, y = self.wlr_constraint.current.cursor_hint
            self.core.warp_pointer(x + self.window.x, y + self.window.y)

        self.core.active_pointer_constraint = None
        self.wlr_constraint.send_deactivated()


class Dnd(HasListeners):
    """A helper for drag and drop functionality."""

    def __init__(self, core: Core, wlr_drag: data_device_manager.Drag):
        self.core = core
        self.wlr_drag = wlr_drag
        self._outputs: Set[Output] = set()

        self.x: float = core.cursor.x
        self.y: float = core.cursor.y
        self.width: int = 0  # Set upon surface commit
        self.height: int = 0

        self.add_listener(wlr_drag.destroy_event, self._on_destroy)
        self.add_listener(wlr_drag.icon.map_event, self._on_icon_map)
        self.add_listener(wlr_drag.icon.unmap_event, self._on_icon_unmap)
        self.add_listener(wlr_drag.icon.destroy_event, self._on_icon_destroy)
        self.add_listener(wlr_drag.icon.surface.commit_event, self._on_icon_commit)

    def finalize(self) -> None:
        self.finalize_listeners()
        self.core.live_dnd = None

    def _on_destroy(self, _listener, _event) -> None:
        logger.debug("Signal: wlr_drag destroy")
        self.finalize()

    def _on_icon_map(self, _listener, _event) -> None:
        logger.debug("Signal: wlr_drag_icon map")
        for output in self._outputs:
            output.damage()

    def _on_icon_unmap(self, _listener, _event) -> None:
        logger.debug("Signal: wlr_drag_icon unmap")
        for output in self._outputs:
            output.damage()

    def _on_icon_destroy(self, _listener, _event) -> None:
        logger.debug("Signal: wlr_drag_icon destroy")

    def _on_icon_commit(self, _listener, _event) -> None:
        self.width = self.wlr_drag.icon.surface.current.width
        self.height = self.wlr_drag.icon.surface.current.height
        self.position(self.core.cursor.x, self.core.cursor.y)

    def position(self, cx: float, cy: float) -> None:
        self.x = cx
        self.y = cy
        self._outputs = {o for o in self.core.outputs if o.contains(self)}
        for output in self._outputs:
            output.damage()


def get_xwayland_atoms(xwayland: xwayland.XWayland) -> Dict[int, str]:
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
