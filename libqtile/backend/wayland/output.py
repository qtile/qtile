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

import os
from typing import TYPE_CHECKING

from wlroots.util.box import Box
from wlroots.util.clock import Timespec
from wlroots.wlr_types import Output as wlrOutput
from wlroots.wlr_types import SceneOutput
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1Layer, LayerSurfaceV1Anchor

from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any

    from cairocffi import ImageSurface
    from pywayland.server import Listener
    from wlroots.wlr_types import SceneBuffer

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.layer import LayerStatic
    from libqtile.backend.wayland.window import WindowType
    from libqtile.backend.wayland.wlrq import Dnd
    from libqtile.config import Screen


class Output(HasListeners):
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        wlr_output.data = self
        self.wallpaper: tuple[SceneBuffer, ImageSurface] | None = None

        # Initialise wlr_output
        wlr_output.init_render(core.allocator, core.renderer)
        wlr_output.set_mode(wlr_output.preferred_mode())
        wlr_output.enable()
        wlr_output.commit()

        # Put new output at far right
        self.x = core.output_layout.get_box().width
        self.y = 0
        core.output_layout.add(wlr_output, self.x, self.y)
        self._scene_output = SceneOutput.create(core.scene, wlr_output)

        self.add_listener(wlr_output.destroy_event, self._on_destroy)
        self.add_listener(wlr_output.frame_event, self._on_frame)

        # The layers enum indexes into this list to get a list of surfaces
        self.layers: list[list[LayerStatic]] = [[] for _ in range(len(LayerShellV1Layer))]

    def finalize(self) -> None:
        self.finalize_listeners()
        self.core.remove_output(self)

    @property
    def screen(self) -> Screen:
        assert self.core.qtile is not None

        if len(self.core.qtile.screens) > 1:
            x, y, w, h = self.get_geometry()
            for screen in self.core.qtile.screens:
                if screen.x == x and screen.y == y:
                    if screen.width == w and screen.height == h:
                        return screen
        return self.core.qtile.current_screen

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: output destroy")
        self.finalize()

    def _on_frame(self, _listener: Listener, _data: Any) -> None:
        try:
            self._scene_output.commit()
        except RuntimeError:
            # Failed to commit scene output; skip.
            return

        self._scene_output.send_frame_done(Timespec.get_monotonic_time())

    def get_geometry(self) -> tuple[int, int, int, int]:
        width, height = self.wlr_output.effective_resolution()
        return int(self.x), int(self.y), width, height

    def organise_layers(self) -> None:
        """Organise the positioning of layer shell surfaces."""
        if not self.wlr_output.enabled:
            return

        logger.debug("Output: organising layers")
        ow, oh = self.wlr_output.effective_resolution()
        full_area = Box(int(self.x), int(self.y), ow, oh)

        for i in range(3, -1, -1):
            # Arrange exclusive surface from top to bottom
            self._organise_layer(LayerShellV1Layer(i), full_area, full_area, exclusive=True)

        for i in range(3, -1, -1):
            # Arrange non-exclusive surface from top to bottom
            self._organise_layer(LayerShellV1Layer(i), full_area, full_area, exclusive=False)

    def _organise_layer(
        self,
        layer: LayerShellV1Layer,
        usable_area: Box,
        full_area: Box,
        *,
        exclusive: bool,
    ) -> None:
        for win in self.layers[layer]:
            state = win.surface.current

            if exclusive != (0 < state.exclusive_zone):
                continue

            # Reserve space if:
            #    - layer is anchored to an edge and both perpendicular edges, or
            #    - layer is anchored to a single edge only.
            space = [0, 0, 0, 0]

            if state.anchor & LayerSurfaceV1Anchor.HORIZONTAL:
                if state.anchor & LayerSurfaceV1Anchor.TOP:
                    space[2] = state.exclusive_zone
                elif state.anchor & LayerSurfaceV1Anchor.BOTTOM:
                    space[3] = state.exclusive_zone
            elif state.anchor & LayerSurfaceV1Anchor.VERTICAL:
                if state.anchor & LayerSurfaceV1Anchor.LEFT:
                    space[0] = state.exclusive_zone
                elif state.anchor & LayerSurfaceV1Anchor.RIGHT:
                    space[1] = state.exclusive_zone
            else:
                # Single edge only
                if state.anchor == LayerSurfaceV1Anchor.TOP:
                    space[2] = state.exclusive_zone
                elif state.anchor == LayerSurfaceV1Anchor.BOTTOM:
                    space[3] = state.exclusive_zone
                if state.anchor == LayerSurfaceV1Anchor.LEFT:
                    space[0] = state.exclusive_zone
                elif state.anchor == LayerSurfaceV1Anchor.RIGHT:
                    space[1] = state.exclusive_zone

            to_reserve: tuple[int, int, int, int] = tuple(space)  # type: ignore
            if win.reserved_space != to_reserve:
                # Don't reserve more space if it's already been reserved
                assert win.qtile is not None
                if win.reserved_space:
                    win.qtile.free_reserved_space(win.reserved_space, self.screen)
                win.reserved_space = to_reserve
                win.qtile.reserve_space(to_reserve, self.screen)

            win.scene_layer.configure(full_area, usable_area)
            win.place(win.node.x, win.node.y, state.desired_width, state.desired_height, 0, None)

    def contains(self, rect: WindowType | Dnd) -> bool:
        """Returns whether the given window is visible on this output."""
        if rect.x + rect.width < self.x:
            return False
        if rect.y + rect.height < self.y:
            return False

        ow, oh = self.wlr_output.effective_resolution()
        if self.x + ow < rect.x:
            return False
        if self.y + oh < rect.y:
            return False

        return True
