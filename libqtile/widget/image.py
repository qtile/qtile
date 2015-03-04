# Copyright (c) 2013 dequis
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
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

import os
import cairocffi

from . import base
from .. import bar

class Image(base._Widget, base.MarginMixin):
    """
        Display a PNG image on the bar.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("scale", True, "Enable/Disable image scaling"),
        ("filename", None, "PNG Image filename. Can contain '~'"),
    ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._Widget.__init__(self, width, **config)
        self.add_defaults(Image.defaults)
        self.add_defaults(base.MarginMixin.defaults)

        # make the default 0 instead
        self._widget_defaults["margin"] = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if not self.filename:
            raise ValueError("Filename not set!")

        self.filename = os.path.expanduser(self.filename)

        try:
            self.image = cairocffi.ImageSurface.create_from_png(self.filename)
        except MemoryError:
            raise ValueError("The image '%s' doesn't seem to be a valid PNG"
                % (self.filename))

        self.pattern = cairocffi.SurfacePattern(self.image)

        self.image_width = self.image.get_width()
        self.image_height = self.image.get_height()

        if self.scale:
            new_height = self.bar.height - (self.margin_y * 2)

            if new_height and self.image_height != new_height:
                scaler = cairocffi.Matrix()
                sp = self.image_height / float(new_height)
                self.image_height = new_height
                self.image_width = int(self.image_width / sp)
                scaler.scale(sp, sp)
                self.pattern.set_matrix(scaler)

    def draw(self):
        self.drawer.clear(self.bar.background)
        self.drawer.ctx.save()
        self.drawer.ctx.translate(self.margin_x, self.margin_y)
        self.drawer.ctx.set_source(self.pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

        self.drawer.draw(offsetx=self.offset, width=self.width)

    def calculate_length(self):
        return self.image_width + (self.margin_x * 2)
