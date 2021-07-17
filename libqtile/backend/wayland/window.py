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
import typing

import cairocffi
import pywayland
from wlroots import ffi
from wlroots.util.edges import Edges
from wlroots.wlr_types import Box, Texture
from wlroots.wlr_types.layer_shell_v1 import LayerSurfaceV1
from wlroots.wlr_types.xdg_shell import (
    XdgPopup,
    XdgSurface,
    XdgTopLevelSetFullscreenEvent,
)

from libqtile import hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.drawer import Drawer
from libqtile.backend.wayland.wlrq import DRM_FORMAT_ARGB8888, HasListeners
from libqtile.command.base import CommandError
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Dict, List, Optional, Tuple, Union

    from wlroots.wlr_types.surface import SubSurface as WlrSubSurface

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.output import Output
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorType

EDGES_TILED = Edges.TOP | Edges.BOTTOM | Edges.LEFT | Edges.RIGHT
EDGES_FLOAT = Edges.NONE


@functools.lru_cache()
def _rgb(color: ColorType) -> ffi.CData:
    """Helper to create and cache float[4] arrays for border painting"""
    if isinstance(color, ffi.CData):
        return color
    return ffi.new("float[4]", utils.rgb(color))


# Window manages XdgSurfaces, Static manages XdgSurfaces and LayerSurfaceV1s
SurfaceType = typing.Union[XdgSurface, LayerSurfaceV1]


class Window(base.Window, HasListeners):
    def __init__(self, core: Core, qtile: Qtile, surface: SurfaceType):
        base.Window.__init__(self)
        self.core = core
        self.qtile = qtile
        self.surface = surface
        self._group: Optional[_Group] = None
        self.popups: List[XdgPopupWindow] = []
        self.subsurfaces: List[SubSurface] = []
        self._mapped: bool = False
        self.x = 0
        self.y = 0
        self.bordercolor: List[ffi.CData] = [_rgb((0, 0, 0, 1))]
        self.opacity: float = 1.0
        self._outputs: List[Output] = []

        # These become non-zero when being mapping for the first time
        self._width: int = 0
        self._height: int = 0

        assert isinstance(surface, XdgSurface)
        if surface.toplevel.title:
            self.name = surface.toplevel.title
        self._app_id: Optional[str] = surface.toplevel.app_id
        surface.set_tiled(EDGES_TILED)

        self._float_state = FloatStates.NOT_FLOATING
        self.float_x: Optional[int] = None
        self.float_y: Optional[int] = None
        self._float_width: int = 0
        self._float_height: int = 0

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.new_popup_event, self._on_new_popup)
        self.add_listener(surface.toplevel.request_fullscreen_event, self._on_request_fullscreen)
        self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
        self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.surface.new_subsurface_event, self._on_new_subsurface)

    def finalize(self):
        self.finalize_listeners()
        for subsurface in self.subsurfaces:
            subsurface.finalize()

    @property
    def wid(self):
        return self._wid

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int) -> None:
        self._width = width

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, height: int) -> None:
        self._height = height

    @property
    def group(self) -> Optional[_Group]:
        return self._group

    @group.setter
    def group(self, group: Optional[_Group]) -> None:
        self._group = group

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        """We keep track of which windows are mapped to we know which to render"""
        if mapped == self._mapped:
            return
        self._mapped = mapped
        if mapped:
            self.core.mapped_windows.append(self)
        else:
            self.core.mapped_windows.remove(self)
        self.core.stack_windows()

    def _on_map(self, _listener, _data):
        logger.debug("Signal: window map")

        if self in self.core.pending_windows:
            self.core.pending_windows.remove(self)
            self._wid = self.core.new_wid()
            logger.debug(f"Managing new top-level window with window ID: {self.wid}")

            # Save the client's desired geometry
            geometry = self.surface.get_geometry()
            self._width = self._float_width = geometry.width
            self._height = self._float_height = geometry.height

            self.qtile.manage(self)

        if self.group.screen:
            self.mapped = True
            self.core.focus_window(self)

    def _on_unmap(self, _listener, _data):
        logger.debug("Signal: window unmap")
        self.mapped = False
        self.damage()
        seat = self.core.seat
        if not seat.destroyed:
            if self.surface.surface == seat.keyboard_state.focused_surface:
                seat.keyboard_clear_focus()

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: window destroy")
        if self.mapped:
            logger.warning("Window destroyed before unmap event.")
            self.mapped = False
        self.qtile.unmanage(self.wid)
        self.finalize()

    def _on_new_popup(self, _listener, xdg_popup: XdgPopup):
        logger.debug("Signal: window new_popup")
        self.popups.append(XdgPopupWindow(self, xdg_popup))

    def _on_request_fullscreen(self, _listener, event: XdgTopLevelSetFullscreenEvent):
        logger.debug("Signal: window request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            self.fullscreen = event.fullscreen

    def _on_set_title(self, _listener, _data):
        logger.debug("Signal: window set_title")
        self.name = self.surface.toplevel.title
        hook.fire('client_name_updated', self)

    def _on_set_app_id(self, _listener, _data):
        logger.debug("Signal: window set_app_id")
        self._app_id = self.surface.toplevel.app_id

    def _on_commit(self, _listener, _data):
        self.damage()

    def _on_new_subsurface(self, _listener, subsurface: WlrSubSurface):
        self.subsurfaces.append(SubSurface(self, subsurface))

    def has_fixed_size(self) -> bool:
        assert isinstance(self.surface, XdgSurface)
        state = self.surface.toplevel._ptr.current
        return (
            0 < state.min_width == state.max_width and
            0 < state.min_height == state.max_height
        )

    def is_transient_for(self) -> Optional[base.WindowType]:
        """What window is this window a transient window for?"""
        assert isinstance(self.surface, XdgSurface)
        parent = self.surface.toplevel.parent
        if parent:
            for win in self.qtile.windows_map.values():
                if not isinstance(win, Internal) and win.surface == parent:  # type: ignore
                    return win
        return None

    def _find_outputs(self):
        """Find the outputs on which this window can be seen."""
        self._outputs = [o for o in self.core.outputs if o.contains(self)]

    def damage(self) -> None:
        for output in self._outputs:
            output.damage()

    def hide(self):
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self):
        if not self.mapped:
            self.surface.map_event.emit()

    def kill(self):
        self.surface.send_close()

    def get_pid(self) -> int:
        pid = pywayland.ffi.new("pid_t *")
        pywayland.lib.wl_client_get_credentials(
            self.surface._ptr.client.client, pid, ffi.NULL, ffi.NULL
        )
        return pid[0]

    def get_wm_class(self) -> Optional[List]:
        if self._app_id:
            return [self._app_id]
        return None

    def togroup(self, group_name=None, *, switch_group=False):
        """Move window to a specified group

        Also switch to that group if switch_group is True.
        """
        if group_name is None:
            group = self.qtile.current_group
        else:
            group = self.qtile.groups_map.get(group_name)
            if group is None:
                raise CommandError("No such group: %s" % group_name)

        if self.group is not group:
            self.hide()
            if self.group:
                if self.group.screen:
                    # for floats remove window offset
                    self.x -= self.group.screen.x
                self.group.remove(self)

            if group.screen and self.x < group.screen.x:
                self.x += group.screen.x
            group.add(self)
            if switch_group:
                group.cmd_toscreen(toggle=False)

    def paint_borders(self, color: Union[ColorType, List[ColorType]], width) -> None:
        if color:
            if isinstance(color, list):
                if len(color) > width:
                    color = color[:width]
                self.bordercolor = [_rgb(c) for c in color]
            else:
                self.bordercolor = [_rgb(color)]
        self.borderwidth = width

    @property
    def floating(self):
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                if not self._float_width:  # These might start as 0
                    self._float_width = self.width
                    self._float_height = self.height
                self._enablefloating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self._float_width,
                    self._float_height
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self._float_width = self.width
                self._float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')

    @property
    def fullscreen(self):
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        self.surface.set_fullscreen(do_full)
        if do_full:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)
            self._enablefloating(
                screen.x,
                screen.y,
                screen.width,
                screen.height,
                new_float_state=FloatStates.FULLSCREEN
            )
            return

        if self._float_state == FloatStates.FULLSCREEN:
            self.floating = False

    @property
    def maximized(self):
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)

            self._enablefloating(
                screen.dx,
                screen.dy,
                screen.dwidth,
                screen.dheight,
                new_float_state=FloatStates.MAXIMIZED
            )
        else:
            if self._float_state == FloatStates.MAXIMIZED:
                self.floating = False

    @property
    def minimized(self):
        return self._float_state == FloatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != FloatStates.MINIMIZED:
                self._enablefloating(new_float_state=FloatStates.MINIMIZED)
        else:
            if self._float_state == FloatStates.MINIMIZED:
                self.floating = False

    def focus(self, warp: bool) -> None:
        self.core.focus_window(self)
        if isinstance(self, base.Internal):
            # self.core.focus_window is enough for internal windows
            return

        if warp and self.qtile.config.cursor_warp:
            self.core.warp_pointer(
                self.x + self.width // 2,
                self.y + self.height // 2,
            )

        if self.group:
            self.group.current_window = self
        hook.fire("client_focus", self)

    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None, respect_hints=False):

        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        if respect_hints:
            state = self.surface.toplevel._ptr.current
            width = max(width, state.min_width)
            height = max(height, state.min_height)
            if state.max_width:
                width = min(width, state.max_width)
            if state.max_height:
                height = min(height, state.max_height)

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self.surface.set_size(int(width), int(height))
        self._width = int(width)
        self._height = int(height)
        self.paint_borders(bordercolor, borderwidth)

        if above and self._mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()

        self._find_outputs()
        self.damage()

    def _tweak_float(self, x=None, y=None, dx=0, dy=0, w=None, h=None, dw=0, dh=0):
        if x is None:
            x = self.x
        x += dx

        if y is None:
            y = self.y
        y += dy

        if w is None:
            w = self.width
        w += dw

        if h is None:
            h = self.height
        h += dh

        if h < 0:
            h = 0
        if w < 0:
            w = 0

        screen = self.qtile.find_closest_screen(x + w // 2, y + h // 2)
        if self.group and screen is not None and screen != self.group.screen:
            self.group.remove(self, force=True)
            screen.group.add(self, force=True)
            self.qtile.focus_screen(screen.index)

        self._reconfigure_floating(x, y, w, h)

    def _enablefloating(self, x=None, y=None, w=None, h=None,
                        new_float_state=FloatStates.FLOATING):
        self._reconfigure_floating(x, y, w, h, new_float_state)

    def _reconfigure_floating(self, x, y, w, h, new_float_state=FloatStates.FLOATING):
        if new_float_state == FloatStates.MINIMIZED:
            self.hide()
        else:
            self.place(
                x, y, w, h,
                self.borderwidth, self.bordercolor, above=True, respect_hints=True
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire('float_change')

    def info(self) -> Dict:
        """Return a dictionary of info."""
        float_info = {
            "x": self.float_x,
            "y": self.float_y,
            "width": self._float_width,
            "height": self._float_height,
        }
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            group=self.group.name if self.group else None,
            id=self.wid,
            float_info=float_info,
            floating=self._float_state != FloatStates.NOT_FLOATING,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN
        )

    def _items(self, name: str) -> ItemT:
        if name == "group":
            return True, []
        elif name == "layout":
            return True, list(range(len(self.group.layouts)))
        elif name == "screen" and self.group.screen is not None:
            return True, []
        return None

    def _select(self, name, sel):
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            return self.group.screen

    def cmd_focus(self, warp: bool = True) -> None:
        """Focuses the window."""
        self.focus(warp)

    def cmd_move_floating(self, dx: int, dy: int) -> None:
        self._tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw: int, dh: int) -> None:
        self._tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x: int, y: int) -> None:
        self._tweak_float(x=x, y=y)

    def cmd_set_size_floating(self, w: int, h: int) -> None:
        self._tweak_float(w=w, h=h)

    def cmd_place(self, x, y, width, height, borderwidth, bordercolor,
                  above=False, margin=None):
        self.place(x, y, width, height, borderwidth, bordercolor, above,
                   margin)

    def cmd_get_position(self) -> Tuple[int, int]:
        return self.x, self.y

    def cmd_get_size(self) -> Tuple[int, int]:
        return self.width, self.height

    def cmd_toggle_floating(self) -> None:
        self.floating = not self.floating

    def cmd_enable_floating(self):
        self.floating = True

    def cmd_disable_floating(self):
        self.floating = False

    def cmd_toggle_maximize(self) -> None:
        self.maximized = not self.maximized

    def cmd_toggle_minimize(self) -> None:
        self.minimized = not self.minimized

    def cmd_toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    def cmd_enable_fullscreen(self) -> None:
        self.fullscreen = True

    def cmd_disable_fullscreen(self) -> None:
        self.fullscreen = False

    def cmd_bring_to_front(self) -> None:
        if self.mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()

    def cmd_kill(self) -> None:
        self.kill()

    def cmd_static(
        self,
        screen: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        self.defunct = True
        if screen is None:
            scr = self.qtile.current_screen
        else:
            scr = self.qtile.screens[screen]
        if self.group:
            self.group.remove(self)
        if x is None:
            x = self.x + self.borderwidth
        if y is None:
            y = self.y + self.borderwidth
        if width is None:
            width = self.width
        if height is None:
            height = self.height

        self.finalize_listeners()
        win = Static(self.core, self.qtile, self.surface, self.wid)
        win._mapped = True
        win.subsurfaces = self.subsurfaces
        win.screen = scr
        win.place(x, y, width, height, 0, None)
        self.qtile.windows_map[self.wid] = win

        if self.mapped:
            z = self.core.mapped_windows.index(self)
            self.core.mapped_windows[z] = win
            self.core.stack_windows()

        hook.fire("client_managed", win)


class Internal(base.Internal, Window):
    """
    Internal windows are simply textures controlled by the compositor.
    """
    texture: Texture

    def __init__(
        self, core: Core, qtile: Qtile, x: int, y: int, width: int, height: int
    ):
        self.core = core
        self.qtile = qtile
        self._mapped: bool = False
        self._wid: int = self.core.new_wid()
        self.x: int = x
        self.y: int = y
        self.opacity: float = 1.0
        self._width: int = width
        self._height: int = height
        self._outputs: List[Output] = []
        self._find_outputs()
        self._reset_texture()

    def finalize(self):
        self.hide()

    def _reset_texture(self):
        clear = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, self.width, self.height)
        with cairocffi.Context(clear) as context:
            context.set_source_rgba(*utils.rgb("#000000"))
            context.paint()

        self.texture = Texture.from_pixels(
            self.core.renderer,
            DRM_FORMAT_ARGB8888,
            cairocffi.ImageSurface.format_stride_for_width(cairocffi.FORMAT_ARGB32, self.width),
            self.width,
            self.height,
            cairocffi.cairo.cairo_image_surface_get_data(clear._pointer),
        )

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = value

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, value: int) -> None:
        self._height = value

    def hide(self) -> None:
        self.mapped = False
        self.damage()

    def unhide(self) -> None:
        self.mapped = True
        self.damage()

    def kill(self) -> None:
        self.hide()
        del self.qtile.windows_map[self.wid]

    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None, respect_hints=False):
        if above and self._mapped:
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()

        self.x = x
        self.y = y
        needs_reset = width != self.width or height != self.height
        self.width = width
        self.height = height

        if needs_reset:
            self._reset_texture()

        self._find_outputs()
        self.damage()

    def info(self) -> Dict:
        """Return a dictionary of info."""
        return dict(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )


class Static(base.Static, Window):
    """
    Static windows represent both regular windows made static by the user and layer
    surfaces created as part of the wlr layer shell protocol.
    """
    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: SurfaceType,
        wid: int,
    ):
        base.Static.__init__(self)
        self.core = core
        self.qtile = qtile
        self.surface = surface
        self.subsurfaces: List[SubSurface] = []
        self._wid = wid
        self._mapped: bool = False
        self.x = 0
        self.y = 0
        self._width = 0
        self._height = 0
        self.borderwidth: int = 0
        self.bordercolor: List[ffi.CData] = [_rgb((0, 0, 0, 1))]
        self.opacity: float = 1.0
        self._outputs: List[Output] = []
        self._float_state = FloatStates.FLOATING
        self.is_layer = False

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)

        if isinstance(surface, LayerSurfaceV1):
            self.is_layer = True
            if surface.output is None:
                surface.output = core.output_layout.output_at(core.cursor.x, core.cursor.y)
            self.output = core.output_from_wlr_output(surface.output)
            self.screen = self.output.screen
            self.mapped = True
            self._outputs.append(self.output)
        else:
            if surface.toplevel.title:
                self.name = surface.toplevel.title
            self._app_id = surface.toplevel.app_id
            self.add_listener(surface.toplevel.set_title_event, self._on_set_title)
            self.add_listener(surface.toplevel.set_app_id_event, self._on_set_app_id)
            self._find_outputs()

    @property
    def mapped(self) -> bool:
        # This is identical to the parent class' version but mypy has a bug that
        # triggers a false positive: https://github.com/python/mypy/issues/1465
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        if mapped == self._mapped:
            return
        self._mapped = mapped

        if isinstance(self.surface, LayerSurfaceV1):
            layer = self.output.layers[self.surface.client_pending.layer]
            if mapped:
                layer.append(self)
            else:
                layer.remove(self)

                if self.reserved_space:
                    self.qtile.free_reserved_space(self.reserved_space, self.screen)
            self.output.organise_layers()

        else:
            if mapped:
                self.core.mapped_windows.append(self)
            else:
                self.core.mapped_windows.remove(self)

        self.core.stack_windows()

    def _on_map(self, _listener, data):
        logger.debug("Signal: window map")
        self.mapped = True
        if self.is_layer:
            self.output.organise_layers()
            self.core.focus_window(self, self.surface.surface)

    def _on_unmap(self, _listener, data):
        logger.debug("Signal: window unmap")
        self.mapped = False
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()
        if self.is_layer:
            self.output.organise_layers()
        self.damage()

    def has_fixed_size(self) -> bool:
        return False

    def kill(self):
        if self.is_layer:
            self.surface.close()
        else:
            self.surface.send_close()

    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None, respect_hints=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        if self.is_layer:
            self.surface.configure(width, height)
        else:
            self.surface.set_size(int(width), int(height))
            self.paint_borders(bordercolor, borderwidth)
        self.damage()

    def cmd_bring_to_front(self) -> None:
        if self.mapped and isinstance(self.surface, XdgSurface):
            self.core.mapped_windows.remove(self)
            self.core.mapped_windows.append(self)
            self.core.stack_windows()
            self.damage()


WindowType = typing.Union[Window, Internal, Static]


class XdgPopupWindow(HasListeners):
    """
    This represents a single `struct wlr_xdg_popup` object and is owned by a single
    parent window (of `Union[WindowType, XdgPopupWindow]`). wlroots does most of the
    work for us, but we need to listen to certain events so that we know when to render
    frames and we need to unconstrain the popups so they are completely visible.
    """
    def __init__(self, parent: Union[WindowType, XdgPopupWindow], xdg_popup: XdgPopup):
        self.parent = parent
        self.xdg_popup = xdg_popup
        self.core: Core = parent.core
        self.popups: List[XdgPopupWindow] = []

        # Keep on output
        if isinstance(parent, XdgPopupWindow):
            # This is a nested XdgPopup
            self.output: Output = parent.output
            self.output_box: Box = parent.output_box
        else:
            # Parent is an XdgSurface; This is a first-level XdgPopup
            box = xdg_popup.base.get_geometry()
            lx, ly = self.core.output_layout.closest_point(parent.x + box.x, parent.y + box.y)
            wlr_output = self.core.output_layout.output_at(lx, ly)
            self.output = wlr_output.data
            box = Box(*self.output.get_geometry())
            box.x = round(box.x - lx)
            box.y = round(box.y - ly)
            self.output_box = box
        xdg_popup.unconstrain_from_box(self.output_box)

        self.add_listener(xdg_popup.base.map_event, self._on_map)
        self.add_listener(xdg_popup.base.unmap_event, self._on_unmap)
        self.add_listener(xdg_popup.base.destroy_event, self._on_destroy)
        self.add_listener(xdg_popup.base.new_popup_event, self._on_new_popup)
        self.add_listener(xdg_popup.base.surface.commit_event, self._on_commit)

    def _on_map(self, _listener, _data):
        logger.debug("Signal: popup map")
        self.output.damage()

    def _on_unmap(self, _listener, _data):
        logger.debug("Signal: popup unmap")
        self.output.damage()

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: popup destroy")
        self.finalize_listeners()
        self.output.damage()

    def _on_new_popup(self, _listener, xdg_popup: XdgPopup):
        logger.debug("Signal: popup new_popup")
        self.popups.append(XdgPopupWindow(self, xdg_popup))

    def _on_commit(self, _listener, _data):
        self.output.damage()


class SubSurface(HasListeners):
    """
    This represents a single `struct wlr_subsurface` object and is owned by a single
    parent window (of `Union[WindowType, SubSurface]`). We only need to track them so
    that we can listen to their commit events and render accordingly.
    """
    def __init__(self, parent: Union[WindowType, SubSurface], subsurface: WlrSubSurface):
        self.parent = parent
        self.subsurfaces: List[SubSurface] = []

        self.add_listener(subsurface.destroy_event, self._on_destroy)
        self.add_listener(subsurface.surface.commit_event, parent._on_commit)
        self.add_listener(subsurface.surface.new_subsurface_event, self._on_new_subsurface)

    def finalize(self):
        self.finalize_listeners()
        for subsurface in self.subsurfaces:
            subsurface.finalize()
        self.parent.subsurfaces.remove(self)

    def _on_destroy(self, _listener, _data):
        self.finalize()

    def _on_commit(self, _listener, _data):
        self.parent._on_commit(None, None)

    def _on_new_subsurface(self, _listener, subsurface: WlrSubSurface):
        self.subsurfaces.append(SubSurface(self, subsurface))
