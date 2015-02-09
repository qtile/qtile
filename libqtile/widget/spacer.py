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
    """
        Just an empty space on the bar. Often used with width equal to
        bar.STRETCH to push bar widgets to the right edge of the screen.
    """
    def __init__(self, width=bar.STRETCH):
        """
            - width: Width of the widget.
              Can be either ``bar.STRETCH`` or a width in pixels.
        """
        base._Widget.__init__(self, width)

    def draw(self):
        self.drawer.clear(self.bar.background)
        self.drawer.draw(self.offset, self.width)
