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

from pywayland.server import Listener
from wlroots.util.clock import Timespec
from wlroots.wlr_types import Box, Matrix
from wlroots.wlr_types import Output as wlrOutput

from libqtile.log_utils import logger


class Output:
    def __init__(self, core, wlr_output):
        self.core = core
        self.renderer = core.renderer
        self.wlr_output = wlr_output
        self.output_layout = self.core.output_layout

        self._on_destroy_listener = Listener(self._on_destroy)
        self._on_frame_listener = Listener(self._on_frame)
        wlr_output.destroy_event.add(self._on_destroy_listener)
        wlr_output.frame_event.add(self._on_frame_listener)

    def finalize(self):
        self._on_destroy_listener.remove()
        self._on_frame_listener.remove()

    def _on_destroy(self, _listener, data):
        logger.debug("Signal: output destroy")
        self.finalize()
        self.core.outputs.remove(self)

    def _on_frame(self, _listener, data):
        now = Timespec.get_monotonic_time()
        wlr_output = self.wlr_output

        if not wlr_output.attach_render():
            logger.error("Could not attach renderer")
            return

        width, height = wlr_output.effective_resolution()
        self.renderer.begin(width, height)
        self.renderer.clear([0, 0, 0, 1])

        for window in self.core.windows:
            if window.mapped:
                window.surface.for_each_surface(self._render_surface, (window, now))

        wlr_output.render_software_cursors()
        self.renderer.end()
        wlr_output.commit()

    def _render_surface(self, surface, sx, sy, data) -> None:
        window, now = data

        texture = surface.get_texture()
        if texture is None:
            return

        wlr_output = self.wlr_output
        ox, oy = self.output_layout.output_coords(wlr_output)  # every time?
        ox += window.x + sx
        oy += window.y + sy
        box = Box(
            int(ox * wlr_output.scale),
            int(oy * wlr_output.scale),
            int(surface.current.width * wlr_output.scale),
            int(surface.current.height * wlr_output.scale),
        )

        inverse = wlrOutput.transform_invert(surface.current.transform)
        matrix = Matrix.project_box(box, inverse, 0, wlr_output.transform_matrix)
        self.renderer.render_texture_with_matrix(texture, matrix, 1)
        surface.send_frame_done(now)

    def get_geometry(self)
        x, y = self.output_layout.output_coords(self.wlr_output)
        width, height = self.wlr_output.effective_resolution()
        return x, y, width, height
