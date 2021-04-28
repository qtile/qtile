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

import typing

from wlroots.util.clock import Timespec
from wlroots.wlr_types import Box, Matrix
from wlroots.wlr_types import Output as wlrOutput
from wlroots.wlr_types.layer_shell_v1 import (
    LayerShellV1Layer,
    LayerSurfaceV1,
    LayerSurfaceV1Anchor,
)

from libqtile import hook
from libqtile.backend.wayland.window import Static, Window
from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import List, Set, Tuple

    from wlroots.wlr_types import Surface

    from libqtile.backend.base import WindowType
    from libqtile.backend.wayland.core import Core


class Output(HasListeners):
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        self.output_layout = self.core.output_layout
        self.wallpaper = None
        self.transform_matrix = wlr_output.transform_matrix
        self.x, self.y = self.output_layout.output_coords(wlr_output)

        self.add_listener(wlr_output.destroy_event, self._on_destroy)
        self.add_listener(wlr_output.frame_event, self._on_frame)

        self._mapped_windows: Set[WindowType] = set()
        hook.subscribe.setgroup(self._get_windows)
        hook.subscribe.group_window_add(self._get_windows)
        hook.subscribe.client_killed(self._get_windows)
        hook.subscribe.client_managed(self._get_windows)

        # The layers enum indexes into this list to get a list of surfaces
        self.layers: List[List[Static]] = [[]] * len(LayerShellV1Layer)

    def finalize(self):
        self.finalize_listeners()

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: output destroy")
        self.finalize()
        self.core.outputs.remove(self)

    def _on_frame(self, _listener, _data):
        now = Timespec.get_monotonic_time()
        wlr_output = self.wlr_output

        with wlr_output:
            self.renderer.begin(*wlr_output.effective_resolution())
            self.renderer.clear([0, 0, 0, 1])

            if self.wallpaper:
                self.renderer.render_texture(self.wallpaper, self.transform_matrix, 0, 0, 1)

            for window in self._mapped_windows:
                rdata = (
                    now,
                    window,
                    self.x + window.x,
                    self.y + window.y,
                    window.opacity,
                    wlr_output.scale,
                )
                window.surface.for_each_surface(self._render_surface, rdata)

            wlr_output.render_software_cursors()
            self.renderer.end()

    def _render_surface(self, surface: Surface, sx: int, sy: int, rdata: Tuple) -> None:
        now, window, wx, wy, opacity, scale = rdata

        texture = surface.get_texture()
        if texture is None:
            return

        x = (wx + sx) * scale
        y = (wy + sy) * scale
        width = surface.current.width * scale
        height = surface.current.height * scale
        transform_matrix = self.wlr_output.transform_matrix

        if surface == window.surface.surface and window.borderwidth:
            bw = window.borderwidth * scale
            bc = window.bordercolor
            border = Box(
                int(x),
                int(y),
                int(width + bw * 2),
                int(bw),
            )
            x += bw
            y += bw
            self.renderer.render_rect(border, bc, transform_matrix)  # Top border
            border.y = int(y + height)
            self.renderer.render_rect(border, bc, transform_matrix)  # Bottom border
            border.y = int(y - bw)
            border.width = int(bw)
            border.height = int(height + bw * 2)
            self.renderer.render_rect(border, bc, transform_matrix)  # Left border
            border.x = int(x + width)
            self.renderer.render_rect(border, bc, transform_matrix)  # Right border

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
        x, y = self.output_layout.output_coords(self.wlr_output)
        width, height = self.wlr_output.effective_resolution()
        return int(x), int(y), width, height

    def _get_windows(self, *args):
        """Get the set of mapped windows for rendering and order them."""
        mapped = []
        mapped.extend([i for i in self.layers[LayerShellV1Layer.BACKGROUND] if i.mapped])
        mapped.extend([i for i in self.layers[LayerShellV1Layer.BOTTOM] if i.mapped])

        for win in self.core.qtile.windows_map.values():
            if win.mapped and isinstance(win, Window):
                mapped.append(win)

        mapped.extend([i for i in self.layers[LayerShellV1Layer.TOP] if i.mapped])
        mapped.extend([i for i in self.layers[LayerShellV1Layer.OVERLAY] if i.mapped])
        self._mapped_windows = mapped

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

                win.place(x, y, ww, wh, 0, None)

        self._get_windows()
