# -*- coding: utf-8 -*-
# Copyright (c) 2012 Florian Mounier
# Copyright (c) 2012 roger
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Craig Barnes
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

from .. import bar
from . import base


class _CrashMe(base._TextBox):
    """A developer widget to force a crash in lavinder

    Pressing left mouse button causes a zero divison error.  Pressing the right
    mouse button causes a cairo draw error.

    Parameters
    ==========

    width :
        A fixed width, or bar.CALCULATED to calculate the width automatically
        (which is recommended).
    """
    orientations = base.ORIENTATION_HORIZONTAL

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "Crash me !", width, **config)

    def _configure(self, lavinder, bar):
        base._Widget._configure(self, lavinder, bar)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=True
        )

    def button_press(self, x, y, button):
        if button == 1:
            1 / 0
        elif button == 3:
            self.text = '<span>\xC3GError'
            self.bar.draw()
