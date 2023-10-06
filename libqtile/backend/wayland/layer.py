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

from typing import TYPE_CHECKING, cast

from pywayland.server import Listener
from wlroots.wlr_types import Output as WlrOutput
from wlroots.wlr_types import SceneTree
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1Layer, LayerSurfaceV1

from libqtile import hook
from libqtile.backend.wayland.output import Output
from libqtile.backend.wayland.window import Static
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi
except ModuleNotFoundError:
    pass

if TYPE_CHECKING:
    from typing import Any

    from wlroots.wlr_types.scene import SceneLayerSurfaceV1

    from libqtile.backend.wayland.core import Core
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType


class LayerStatic(Static[LayerSurfaceV1]):
    """A static window belonging to the layer shell."""

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        surface: LayerSurfaceV1,
        wid: int,
    ):
        Static.__init__(self, core, qtile, surface, wid)

        self.desired_width = 0
        self.desired_height = 0

        self.data_handle = ffi.new_handle(self)
        surface.data = self.data_handle

        # Determine which output this window is to appear on
        if wlr_output := surface.output:
            logger.debug("Layer surface requested output: %s", wlr_output.name)
        else:
            wlr_output = cast(
                WlrOutput, core.output_layout.output_at(core.cursor.x, core.cursor.y)
            )
            logger.debug("Layer surface given output: %s", wlr_output.name)
            surface.output = wlr_output

        output = cast(Output, wlr_output.data)
        self.output = output
        self.screen = output.screen

        # Add the window to the scene graph
        parent_tree = core.layer_trees[surface.pending.layer]
        self.scene_layer: SceneLayerSurfaceV1 = core.scene.layer_surface_v1_create(
            parent_tree, surface
        )
        self.tree: SceneTree = self.scene_layer.tree
        self.tree.node.data = self.data_handle
        self.popup_tree = SceneTree.create(parent_tree)  # Popups get their own tree
        self.popup_tree.node.data = self.data_handle

        # Set up listeners
        self.add_listener(surface.surface.map_event, self._on_map)
        self.add_listener(surface.surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)

        # Temporarily set the layer's current state to pending so that we can easily
        # arrange it. TODO: how much of this is needed?
        self._layer = surface.pending.layer
        old_state = surface.current
        surface.current = surface.pending
        self.unhide()
        self.output.organise_layers()
        surface.current = old_state
        self._move_to_layer(old_state.layer)

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        if self.surface.output and self.surface.output.data:
            output = self.surface.output.data
            if output != self.output:
                # The window wants to move to a different output.
                if self.tree.node.enabled:
                    self.output.layers[self._layer].remove(self)
                    output.layers[self._layer].append(self)
                self.output = output

        pending = self.surface.pending
        if (
            self._layer != pending.layer
            or self._width != pending.desired_width
            or self._height != pending.desired_height
        ):
            # The window has changed its desired layer or dimensions.
            self._move_to_layer(pending.layer)

    def _move_to_layer(self, layer: LayerShellV1Layer) -> None:
        new_parent = self.core.layer_trees[layer]
        self.tree.node.reparent(new_parent)
        self.popup_tree.node.reparent(new_parent)

        if self.tree.node.enabled:
            # If we're mapped, we also need to update the lists on the output.
            self.output.layers[self._layer].remove(self)
            self.output.layers[layer].append(self)
            self.output.organise_layers()

        self._layer = layer

    def finalize(self) -> None:
        super().finalize()
        self.popup_tree.node.destroy()

    def kill(self) -> None:
        self.surface.destroy()

    def hide(self) -> None:
        if self.core.exclusive_layer is self:
            self.core.exclusive_layer = None

        if self.reserved_space:
            self.qtile.free_reserved_space(self.reserved_space, self.screen)
            self.reserved_space = None

        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()

        if self in self.output.layers[self._layer]:
            self.tree.node.set_enabled(enabled=False)
            # TODO also toggle popup_tree
            self.output.layers[self._layer].remove(self)
            self.output.organise_layers()

    def unhide(self) -> None:
        if self not in self.output.layers[self._layer]:
            self.tree.node.set_enabled(enabled=True)
            self.output.layers[self._layer].append(self)
            self.output.organise_layers()

    def focus(self, _warp: bool = True) -> None:
        self.core.focus_window(self)
        hook.fire("client_focus", self)

    def place(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        borderwidth: int,
        bordercolor: ColorsType | None,
        above: bool = False,
        margin: int | list[int] | None = None,
        respect_hints: bool = False,
    ) -> None:
        self.x = x
        self.y = y
        self.tree.node.set_position(x, y)
        self.popup_tree.node.set_position(x, y)
        # The actual resizing is done by `Output`.
        self._width = width
        self._height = height

    @expose_command()
    def bring_to_front(self) -> None:
        self.tree.node.raise_to_top()
