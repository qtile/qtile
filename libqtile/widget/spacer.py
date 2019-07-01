# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 Tim Neumann
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Tycho Andersen
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

from .. import bar
from . import base


class Spacer(base._Widget):
    """Just an empty space on the bar

    Often used with length equal to bar.STRETCH to push bar widgets to the
    right or bottom edge of the screen.

    Parameters
    ==========
    length :
        Length of the widget.  Can be either ``bar.STRETCH`` or a length in
        pixels.
    width :
        DEPRECATED, same as ``length``.
    """
    orientations = base.ORIENTATION_BOTH
    defaults = [
        ("background", None, "Widget background color")
    ]

    def __init__(self, length=bar.STRETCH, width=None, **config):
        """
        """
        # 'width' was replaced by 'length' since the widget can be installed in
        # vertical bars
        if width is not None:
            base.deprecated('width kwarg or positional argument is '
                            'deprecated. Please use length.')
            length = width

        base._Widget.__init__(self, length, **config)
        self.add_defaults(Spacer.defaults)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        if self.bar.horizontal:
            self.drawer.draw(offsetx=self.offset, width=self.length)
        else:
            self.drawer.draw(offsety=self.offset, height=self.length)
