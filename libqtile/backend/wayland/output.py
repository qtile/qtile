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

from pywayland.server import Listener
from wlroots.util.clock import Timespec
from wlroots.wlr_types import Box, Matrix
from wlroots.wlr_types import Output as wlrOutput

from libqtile import hook
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Set, Tuple

    from wlroots.wlr_types import Surface

    from libqtile.backend.base import WindowType
    from libqtile.backend.wayland.core import Core


class Output:
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        self.output_layout = self.core.output_layout
        self.wallpaper = None
        self.transform_matrix = wlr_output.transform_matrix
        self.x, self.y = self.output_layout.output_coords(wlr_output)

        self._on_destroy_listener = Listener(self._on_destroy)
        self._on_frame_listener = Listener(self._on_frame)
        wlr_output.destroy_event.add(self._on_destroy_listener)
        wlr_output.frame_event.add(self._on_frame_listener)

        self._mapped_windows: Set[WindowType] = set()
        hook.subscribe.setgroup(self._get_windows)
        hook.subscribe.group_window_add(self._get_windows)
        hook.subscribe.client_killed(self._get_windows)
        hook.subscribe.client_managed(self._get_windows)

    def finalize(self):
        self._on_destroy_listener.remove()
        self._on_frame_listener.remove()

    def _on_destroy(self, _listener, _data):
        logger.debug("Signal: output destroy")
        self.finalize()
        self.core.outputs.remove(self)

    def _on_frame(self, _listener, _data):
        now = Timespec.get_monotonic_time()
        wlr_output = self.wlr_output

        if not wlr_output.attach_render():
            logger.error("Could not attach renderer")
            return

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
        wlr_output.commit()

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
        """Get the set of mapped windows for rendering."""
        mapped = set()
        for win in self.core.qtile.windows_map.values():
            if win.mapped:
                mapped.add(win)
        self._mapped_windows = mapped
