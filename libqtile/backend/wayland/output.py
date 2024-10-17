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
from wlroots.wlr_types import OutputState, SceneOutput
from wlroots.wlr_types.layer_shell_v1 import (
    LayerShellV1Layer,
    LayerSurfaceV1KeyboardInteractivity,
)
from wlroots.wlr_types.output import CustomMode

from libqtile.backend.wayland.wlrq import HasListeners
from libqtile.config import ScreenRect
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any

    from pywayland.server import Listener
    from wlroots.wlr_types.output import OutputEventRequestState

    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.layer import LayerStatic
    from libqtile.backend.wayland.window import WindowType
    from libqtile.config import Screen


class Output(HasListeners):
    def __init__(self, core: Core, wlr_output: wlrOutput):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        self._reserved_space = (0, 0, 0, 0)

        # These will get updated on the output layout's change event
        self.x = 0
        self.y = 0

        self.scene_output = SceneOutput.create(core.scene, wlr_output)
        wlr_output.init_render(core.allocator, core.renderer)

        # The output may be disabled, switch it on.
        state = OutputState()
        state.set_enabled(True)

        # Select the output's preferred mode.
        if mode := wlr_output.preferred_mode():
            state.set_mode(mode)

        # During tests, we want to fix the geometry of the 1 or 2 outputs.
        if wlr_output.is_headless and "PYTEST_CURRENT_TEST" in os.environ:
            if not core.get_enabled_outputs():
                # First test output
                state.set_custom_mode(CustomMode(width=800, height=600, refresh=0))
            else:
                # Second test output
                state.set_custom_mode(CustomMode(width=640, height=480, refresh=0))

        # Commit this initial state.
        wlr_output.commit(state)
        state.finish()

        wlr_output.data = self

        self.add_listener(wlr_output.destroy_event, self._on_destroy)
        self.add_listener(wlr_output.frame_event, self._on_frame)
        self.add_listener(wlr_output.request_state_event, self._on_request_state)

        # The layers enum indexes into this list to get a list of surfaces
        self.layers: list[list[LayerStatic]] = [[] for _ in range(len(LayerShellV1Layer))]

    def finalize(self) -> None:
        self.finalize_listeners()
        self.core.remove_output(self)
        self.scene_output.destroy()

    def __repr__(self) -> str:
        i = self.get_screen_info()
        return f"<Output ({i.x}, {i.y}, {i.width}, {i.height})>"

    @property
    def screen(self) -> Screen:
        assert self.core.qtile is not None

        for screen in self.core.qtile.screens:
            # Outputs alias if they have the same (x, y) and share the same Screen, so
            # we don't need to check the if the width and height match the Screen's.
            if screen.x == self.x and screen.y == self.y:
                return screen

        return self.core.qtile.current_screen

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: output destroy")
        self.finalize()

    def _on_frame(self, _listener: Listener, _data: Any) -> None:
        self.core.configure_node_opacity(self.core.windows_tree.node)
        try:
            self.scene_output.commit()
        except RuntimeError:
            # Failed to commit scene output; skip rendering.
            pass

        # Inform clients of the frame
        self.scene_output.send_frame_done(Timespec.get_monotonic_time())

    def _on_request_state(self, _listener: Listener, request: OutputEventRequestState) -> None:
        logger.debug("Signal: output request_state")
        self.wlr_output.commit(request.state)

    def get_screen_info(self) -> ScreenRect:
        width, height = self.wlr_output.effective_resolution()
        return ScreenRect(int(self.x), int(self.y), width, height)

    def organise_layers(self) -> None:
        """Organise the positioning of layer shell surfaces."""
        logger.debug("Output: organising layers")
        ow, oh = self.wlr_output.effective_resolution()

        # These rects are in output layout coordinates
        full_area = Box(self.x, self.y, ow, oh)
        usable_area = Box(self.x, self.y, ow, oh)

        for layer in reversed(LayerShellV1Layer):
            # Arrange exclusive surface from top to bottom
            self._organise_layer(layer, full_area, usable_area, exclusive=True)

        # TODO: can this be a geometry?
        # The positions used for reserving space are screen-relative coordinates
        new_reserved_space = (
            usable_area.x - self.x,  # left
            self.x + ow - usable_area.x - usable_area.width,  # right
            usable_area.y - self.y,  # top
            self.y + oh - usable_area.y - usable_area.height,  # bottom
        )
        delta = tuple(new - old for new, old in zip(new_reserved_space, self._reserved_space))
        if any(delta):
            self.core.qtile.reserve_space(delta, self.screen)  # type: ignore
            self._reserved_space = new_reserved_space

        for layer in reversed(LayerShellV1Layer):
            # Arrange non-exclusive surface from top to bottom
            self._organise_layer(layer, full_area, usable_area, exclusive=False)

        # Find topmost keyboard interactive layer
        for layer in (LayerShellV1Layer.OVERLAY, LayerShellV1Layer.TOP):
            for win in self.layers[layer]:
                if (
                    win.surface.current.keyboard_interactive
                    == LayerSurfaceV1KeyboardInteractivity.EXCLUSIVE
                ):
                    self.core.exclusive_layer = win
                    self.core.focus_window(win)
                    return
                if self.core.exclusive_layer is win:
                    # This window previously had exclusive focus, but no longer wants it.
                    self.core.exclusive_layer = None

    def _organise_layer(
        self,
        layer: LayerShellV1Layer,
        full_area: Box,
        usable_area: Box,
        *,
        exclusive: bool,
    ) -> None:
        for win in self.layers[layer]:
            state = win.surface.current

            if exclusive != (0 < state.exclusive_zone):
                continue

            win.scene_layer.configure(full_area, usable_area)
            win.place(
                win.tree.node.x,
                win.tree.node.y,
                state.desired_width,
                state.desired_height,
                0,
                None,
            )

    def contains(self, rect: WindowType) -> bool:
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
