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

from __future__ import division

import os

from . import base
from .. import bar
from ..images import Img

class Image(base._Widget, base.MarginMixin):
    """Display a PNG image on the bar"""
    orientations = base.ORIENTATION_BOTH
    defaults = [
        ("scale", True, "Enable/Disable image scaling"),
        ("filename", None, "Image filename. Can contain '~'"),
    ]

    def __init__(self, length=bar.CALCULATED, width=None, **config):
        # 'width' was replaced by 'length' since the widget can be installed in
        # vertical bars
        if width is not None:
            base.deprecated('width kwarg or positional argument is '
                            'deprecated. Please use length.')
            length = width

        base._Widget.__init__(self, length, **config)
        self.add_defaults(Image.defaults)
        self.add_defaults(base.MarginMixin.defaults)

        # make the default 0 instead
        self._variable_defaults["margin"] = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if not self.filename:
            raise ValueError("Filename not set!")

        self.filename = os.path.expanduser(self.filename)
        img = Img.from_path(self.filename)
        self.img = img
        if not self.scale:
            return
        width0, height0 = img.width, img.height
        img.lock_aspect_ratio = True
        if self.bar.horizontal:
            new_height = self.bar.height - (self.margin_y * 2)
            if (new_height > 0) and (new_height != height0):
                img.height = new_height
        else:
            new_width = self.bar.width - (self.margin_x * 2)
            if (new_width > 0) and (new_width != width0):
                img.width = new_width

    def draw(self):
        self.drawer.clear(self.bar.background)
        self.drawer.ctx.save()
        self.drawer.ctx.translate(self.margin_x, self.margin_y)
        self.drawer.ctx.set_source(self.img.pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

        if self.bar.horizontal:
            self.drawer.draw(offsetx=self.offset, width=self.width)
        else:
            self.drawer.draw(offsety=self.offset, height=self.width)

    def calculate_length(self):
        if self.bar.horizontal:
            return self.img.width + (self.margin_x * 2)
        else:
            return self.img.height + (self.margin_y * 2)
