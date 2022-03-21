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

from pywayland.protocol.wayland.wl_output import WlOutput
from wlroots.util.box import Box
from wlroots.util.clock import Timespec
from wlroots.util.region import PixmanRegion32
from wlroots.wlr_types import Matrix
from wlroots.wlr_types import Output as wlrOutput
from wlroots.wlr_types import OutputDamage
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1Layer, LayerSurfaceV1Anchor

from libqtile.backend.wayland.window import Internal, LayerStatic
from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any, Sequence

    from pywayland.server import Listener
    from wlroots.wlr_types import Surface, Texture

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.window import WindowType
    from libqtile.backend.wayland.wlrq import Dnd
    from libqtile.config import Screen

no_transform = WlOutput.transform.normal


class Output(HasListeners):
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        wlr_output.data = self
        self.output_layout = self.core.output_layout
        self._damage: OutputDamage = OutputDamage(wlr_output)
        self.wallpaper: Texture | None = None
        self.x, self.y = self.output_layout.output_coords(wlr_output)

        self.add_listener(wlr_output.destroy_event, self._on_destroy)
        self.add_listener(self._damage.frame_event, self._on_frame)

        # The layers enum indexes into this list to get a list of surfaces
        self.layers: list[list[LayerStatic]] = [[] for _ in range(len(LayerShellV1Layer))]

        # This is run during tests, when we want to fix the output's geometry
        if wlr_output.is_headless and "PYTEST_CURRENT_TEST" in os.environ:
            assert len(core.outputs) < 2, "This should not be reached"
            if not core.outputs:
                # First test output
                wlr_output.set_custom_mode(800, 600, 0)
            else:
                # Second test output
                wlr_output.set_custom_mode(640, 480, 0)
            wlr_output.commit()

    def finalize(self) -> None:
        self.core.remove_output(self)
        self.finalize_listeners()

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
        with PixmanRegion32() as damage:
            try:
                if not self._damage.attach_render(damage):
                    # No new frame needed.
                    self.wlr_output.rollback()
                    return
            except RuntimeError:
                # Failed to attach render; skip.
                return

            with self.wlr_output as wlr_output:
                if not damage.not_empty():
                    # No damage, only buffer swap needed.
                    return

                now = Timespec.get_monotonic_time()
                scale = wlr_output.scale
                transform_matrix = wlr_output.transform_matrix

                with self.renderer.render(
                    wlr_output._ptr.width, wlr_output._ptr.height
                ) as renderer:

                    if self.wallpaper:
                        width, height = wlr_output.effective_resolution()
                        box = Box(0, 0, int(width * scale), int(height * scale))
                        matrix = Matrix.project_box(box, no_transform, 0, transform_matrix)
                        renderer.render_texture_with_matrix(self.wallpaper, matrix, 1)
                    else:
                        renderer.clear([0, 0, 0, 1])

                    mapped: Sequence[WindowType] = (
                        self.layers[LayerShellV1Layer.BACKGROUND]
                        + self.layers[LayerShellV1Layer.BOTTOM]
                        + self.core.mapped_windows  # type: ignore
                        + self.layers[LayerShellV1Layer.TOP]
                        + self.layers[LayerShellV1Layer.OVERLAY]
                    )

                    for window in mapped:
                        if isinstance(window, Internal):
                            box = Box(
                                int((window.x - self.x) * scale),
                                int((window.y - self.y) * scale),
                                int(window.width * scale),
                                int(window.height * scale),
                            )
                            matrix = Matrix.project_box(box, no_transform, 0, transform_matrix)
                            renderer.render_texture_with_matrix(
                                window.texture, matrix, window.opacity
                            )
                        else:
                            rdata = (
                                now,
                                window,
                                window.x - self.x,  # layout coordinates -> output coordinates
                                window.y - self.y,
                                window.opacity,
                                scale,
                                transform_matrix,
                            )
                            window.surface.for_each_surface(self._render_surface, rdata)

                    if self.core.live_dnd:
                        self._render_dnd_icon(self.core.live_dnd, now, scale, transform_matrix)

                    wlr_output.render_software_cursors(damage=damage)

    def _render_surface(self, surface: Surface, sx: int, sy: int, rdata: tuple) -> None:
        texture = surface.get_texture()
        if texture is None:
            return

        now, window, wx, wy, opacity, scale, transform_matrix = rdata
        x = (wx + sx) * scale
        y = (wy + sy) * scale
        width = surface.current.width * scale
        height = surface.current.height * scale

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

    def _render_dnd_icon(
        self, dnd: Dnd, now: Timespec, scale: float, transform_matrix: Matrix
    ) -> None:
        """Render the drag-n-drop icon if there is one."""
        icon = dnd.wlr_drag.icon
        if icon.mapped:
            texture = icon.surface.get_texture()
            if texture:
                box = Box(
                    int((dnd.x - self.x) * scale),
                    int((dnd.y - self.y) * scale),
                    int(icon.surface.current.width * scale),
                    int(icon.surface.current.height * scale),
                )
                inverse = wlrOutput.transform_invert(icon.surface.current.transform)
                matrix = Matrix.project_box(box, inverse, 0, transform_matrix)
                self.renderer.render_texture_with_matrix(texture, matrix, 1)
                icon.surface.send_frame_done(now)

    def get_geometry(self) -> tuple[int, int, int, int]:
        width, height = self.wlr_output.effective_resolution()
        return int(self.x), int(self.y), width, height

    def organise_layers(self) -> None:
        """Organise the positioning of layer shell surfaces."""
        logger.debug("Output: organising layers")
        ow, oh = self.wlr_output.effective_resolution()

        for layer in self.layers:
            for win in layer:
                state = win.surface.current
                margin = state.margin
                ww = win.desired_width = state.desired_width
                wh = win.desired_height = state.desired_height

                # Horizontal axis
                if (state.anchor & LayerSurfaceV1Anchor.HORIZONTAL) and ww == 0:
                    x = margin.left
                    ww = ow - margin.left - margin.right
                elif state.anchor & LayerSurfaceV1Anchor.LEFT:
                    x = margin.left
                elif state.anchor & LayerSurfaceV1Anchor.RIGHT:
                    x = ow - ww - margin.right
                else:
                    x = int(ow / 2 - ww / 2)

                # Vertical axis
                if (state.anchor & LayerSurfaceV1Anchor.VERTICAL) and wh == 0:
                    y = margin.top
                    wh = oh - margin.top - margin.bottom
                elif state.anchor & LayerSurfaceV1Anchor.TOP:
                    y = margin.top
                elif state.anchor & LayerSurfaceV1Anchor.BOTTOM:
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

                    to_reserve: tuple[int, int, int, int] = tuple(space)  # type: ignore
                    if win.reserved_space != to_reserve:
                        # Don't reserve more space if it's already been reserved
                        assert self.core.qtile is not None
                        self.core.qtile.reserve_space(to_reserve, self.screen)
                        win.reserved_space = to_reserve

                win.place(int(x + self.x), int(y + self.y), int(ww), int(wh), 0, None)

        self.core.stack_windows()

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

    def damage(self) -> None:
        """Damage this output so it gets re-rendered."""
        if self.wlr_output.enabled:
            self._damage.add_whole()
