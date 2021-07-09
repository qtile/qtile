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
import typing

from wlroots.util.clock import Timespec
from wlroots.util.region import PixmanRegion32
from wlroots.wlr_types import Box, Matrix
from wlroots.wlr_types import Output as wlrOutput
from wlroots.wlr_types import OutputDamage
from wlroots.wlr_types.layer_shell_v1 import (
    LayerShellV1Layer,
    LayerSurfaceV1,
    LayerSurfaceV1Anchor,
)

from libqtile.backend.wayland.window import Internal, Static
from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import List, Tuple

    from wlroots.wlr_types import Surface

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.window import WindowType
    from libqtile.config import Screen


class Output(HasListeners):
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        wlr_output.data = self
        self.output_layout = self.core.output_layout
        self._damage: OutputDamage = OutputDamage(wlr_output)
        self.wallpaper = None
        self.transform_matrix = wlr_output.transform_matrix
        self.x, self.y = self.output_layout.output_coords(wlr_output)

        self.add_listener(wlr_output.destroy_event, self._on_destroy)
        self.add_listener(self._damage.frame_event, self._on_frame)

        # The layers enum indexes into this list to get a list of surfaces
        self.layers: List[List[Static]] = [[] for _ in range(len(LayerShellV1Layer))]

        # This is run during tests, when we want to fix the output's geometry
        if wlr_output.is_headless and "PYTEST_CURRENT_TEST" in os.environ:
            assert len(core.outputs) < 2, "This should not be reached"
            if not core.outputs:
                # First test output
                wlr_output.set_custom_mode(800, 600, 0)
            else:
                # Secound test output
                wlr_output.set_custom_mode(640, 480, 0)
            wlr_output.commit()

    def finalize(self):
        self.core.outputs.remove(self)
        self.finalize_listeners()

    @property
    def screen(self) -> Screen:
        assert self.core.qtile is not None
        x, y, w, h = self.get_geometry()
        for screen in self.core.qtile.screens:
            if screen.x == x and screen.y == y:
                if screen.width == w and screen.height == h:
                    return screen
        return self.core.qtile.current_screen

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: output destroy")
        self.finalize()

    def _on_frame(self, _listener, _data):
        wlr_output = self.wlr_output

        with PixmanRegion32() as damage:
            if not self._damage.attach_render(damage):
                # no new frame needed
                wlr_output.rollback()
                return

            with wlr_output:
                if not damage.not_empty():
                    # No damage, only buffer swap needed
                    return

                now = Timespec.get_monotonic_time()
                renderer = self.renderer
                renderer.begin(*wlr_output.effective_resolution())

                if self.wallpaper:
                    renderer.render_texture(self.wallpaper, self.transform_matrix, 0, 0, 1)
                else:
                    renderer.clear([0, 0, 0, 1])

                mapped = self.layers[LayerShellV1Layer.BACKGROUND] \
                    + self.layers[LayerShellV1Layer.BOTTOM] \
                    + self.core.mapped_windows \
                    + self.layers[LayerShellV1Layer.TOP] \
                    + self.layers[LayerShellV1Layer.OVERLAY]

                for window in mapped:
                    if isinstance(window, Internal):
                        renderer.render_texture(
                            window.texture,
                            self.transform_matrix,
                            window.x - self.x,  # layout coordinates -> output coordinates
                            window.y - self.y,
                            window.opacity,
                        )
                    else:
                        rdata = (
                            now,
                            window,
                            window.x - self.x,  # layout coordinates -> output coordinates
                            window.y - self.y,
                            window.opacity,
                            wlr_output.scale,
                        )
                        window.surface.for_each_surface(self._render_surface, rdata)

                wlr_output.render_software_cursors(damage=damage)
                renderer.end()

    def _render_surface(self, surface: Surface, sx: int, sy: int, rdata: Tuple) -> None:
        texture = surface.get_texture()
        if texture is None:
            return

        now, window, wx, wy, opacity, scale = rdata
        x = (wx + sx) * scale
        y = (wy + sy) * scale
        width = surface.current.width * scale
        height = surface.current.height * scale
        transform_matrix = self.transform_matrix

        if window.borderwidth:
            bw = int(window.borderwidth * scale)

            if surface == window.surface.surface:
                outer_w = width + bw * 2
                outer_h = height + bw * 2
                num = len(window.bordercolor)
                bws = [bw // num] * num
                for i in range(bw % num):
                    bws[i] += 1
                coord = 0
                for i, bc in enumerate(window.bordercolor):
                    border = Box(
                        int(x + coord),
                        int(y + coord),
                        int(outer_w - coord * 2),
                        int(bws[i]),
                    )
                    self.renderer.render_rect(border, bc, transform_matrix)  # Top border
                    border.y = int(y + outer_h - bws[i] - coord)
                    self.renderer.render_rect(border, bc, transform_matrix)  # Bottom border
                    border.y = int(y + coord)
                    border.width = int(bws[i])
                    border.height = int(outer_h - coord * 2)
                    self.renderer.render_rect(border, bc, transform_matrix)  # Left border
                    border.x = int(x + outer_w - bws[i] - coord)
                    self.renderer.render_rect(border, bc, transform_matrix)  # Right border
                    coord += bws[i]

            x += bw
            y += bw

        box = Box(
            int(x),
            int(y),
            int(width),
            int(height),
        )

        inverse = wlrOutput.transform_invert(surface.current.transform)
        matrix = Matrix.project_box(box, inverse, 0, transform_matrix)
        self.renderer.render_texture_with_matrix(texture, matrix, opacity)
        surface.send_frame_done(now)

    def get_geometry(self) -> Tuple[int, int, int, int]:
        width, height = self.wlr_output.effective_resolution()
        return int(self.x), int(self.y), width, height

    def organise_layers(self) -> None:
        """Organise the positioning of layer shell surfaces."""
        logger.info("Output: organising layers")
        ow, oh = self.wlr_output.effective_resolution()

        for layer in self.layers:
            for win in layer:
                assert isinstance(win.surface, LayerSurfaceV1)
                state = win.surface.current
                margin = state.margin
                ww = state.desired_width
                wh = state.desired_height

                # Horizontal axis
                if (state.anchor & LayerSurfaceV1Anchor.HORIZONTAL) and ww == 0:
                    x = margin.left
                    ww = ow - margin.left - margin.right
                elif (state.anchor & LayerSurfaceV1Anchor.LEFT):
                    x = margin.left
                elif (state.anchor & LayerSurfaceV1Anchor.RIGHT):
                    x = ow - ww - margin.right
                else:
                    x = int(ow / 2 - ww / 2)

                # Vertical axis
                if (state.anchor & LayerSurfaceV1Anchor.VERTICAL) and wh == 0:
                    y = margin.top
                    wh = oh - margin.top - margin.bottom
                elif (state.anchor & LayerSurfaceV1Anchor.TOP):
                    y = margin.top
                elif (state.anchor & LayerSurfaceV1Anchor.BOTTOM):
                    y = oh - wh - margin.bottom
                else:
                    y = int(oh / 2 - wh / 2)

                if ww <= 0 or wh <= 0:
                    win.kill()
                    continue

                if 0 < state.exclusive_zone:
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

                    to_reserve: Tuple[int, int, int, int] = tuple(space)  # type: ignore
                    if win.reserved_space != to_reserve:
                        # Don't reserve more space if it's already been reserved
                        assert self.core.qtile is not None
                        self.core.qtile.reserve_space(to_reserve, self.screen)
                        win.reserved_space = to_reserve

                win.place(x + self.x, y + self.y, ww, wh, 0, None)

        self.core.stack_windows()

    def contains(self, win: WindowType) -> bool:
        """Returns whether the given window is visible on this output."""
        if win.x + win.width < self.x:
            return False
        if win.y + win.height < self.y:
            return False

        ow, oh = self.wlr_output.effective_resolution()
        if self.x + ow < win.x:
            return False
        if self.y + oh < win.y:
            return False

        return True

    def damage(self) -> None:
        """Damage this output so it gets re-rendered."""
        if self.wlr_output.enabled:
            self._damage.add_whole()
