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
from wlroots.wlr_types.layer_shell_v1 import LayerShellV1Layer, LayerSurfaceV1

from libqtile.backend.wayland.subsurface import SubSurface
from libqtile.backend.wayland.window import Static
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

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
        self.subsurfaces: list[SubSurface] = []

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)

        self._layer = LayerShellV1Layer.BACKGROUND
        self.desired_width = 0
        self.desired_height = 0
        if surface.output is None:
            surface.output = core.output_layout.output_at(core.cursor.x, core.cursor.y)

        if surface.output:
            output = surface.output.data
            if output:
                self.output = output
                self.screen = self.output.screen

        self.mapped = True
        self._outputs.add(self.output)

    def finalize(self) -> None:
        Static.finalize(self)
        for subsurface in self.subsurfaces:
            subsurface.finalize()

    @property
    def mapped(self) -> bool:
        return self._mapped

    @mapped.setter
    def mapped(self, mapped: bool) -> None:
        if mapped == self._mapped:
            return
        self._mapped = mapped

        self._layer = self.surface.pending.layer
        if mapped:
            self.output.layers[self._layer].append(self)
            self.core.stack_windows()
        else:
            self.output.layers[self._layer].remove(self)
            if self in self.core.stacked_windows:
                self.core.stacked_windows.remove(self)

            if self.reserved_space:
                self.qtile.free_reserved_space(self.reserved_space, self.screen)

        self.output.organise_layers()

    def _on_map(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: layerstatic map")
        self.mapped = True
        self.output.organise_layers()
        self.focus(False)

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: layerstatic unmap")
        self.mapped = False
        if self.surface.surface == self.core.seat.keyboard_state.focused_surface:
            group = self.qtile.current_screen.group
            if group.current_window:
                group.focus(group.current_window, warp=self.qtile.config.cursor_warp)
            else:
                self.core.seat.keyboard_clear_focus()
        self.output.organise_layers()
        self.damage()

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        output = self.surface.output and self.surface.output.data
        if output and self.output != output:
            prev_output = self.output
            self.output = output
            self._outputs.remove(prev_output)
            self._outputs.add(output)
            if self._mapped:
                prev_output.layers[self._layer].remove(self)
                self.output.layers[self._layer].append(self)

        current = self.surface.current
        if (
            self._layer != current.layer
            or self.desired_width != current.desired_width
            or self.desired_height != current.desired_height
        ):
            if self._mapped:
                self.output.layers[self._layer].remove(self)
                self._layer = current.layer
                self.output.layers[self._layer].append(self)
                self.core.stack_windows()
            self.output.organise_layers()
        self.damage()

    def kill(self) -> None:
        self.surface.destroy()

    def hide(self) -> None:
        if self.mapped:
            self.surface.unmap_event.emit()

    def unhide(self) -> None:
        if not self.mapped:
            self.surface.map_event.emit()

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
        self._width = width
        self._height = height
        self.surface.configure(width, height)
        self.damage()

    @expose_command()
    def bring_to_front(self) -> None:
        pass
