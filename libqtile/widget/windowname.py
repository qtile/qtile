# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2010 matt
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 Tim Neumann
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
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

from .. import hook, bar
from . import base


class WindowName(base._TextBox):
    """
        Displays the name of the window that currently has focus.
    """
    orientations = base.ORIENTATION_HORIZONTAL

    def __init__(self, width=bar.STRETCH, **config):
        base._TextBox.__init__(self, width=width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.window_name_change(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        state = ''
        if w is None:
            pass
        elif w.maximized:
            state = '[] '
        elif w.minimized:
            state = '_ '
        elif w.floating:
            state = 'V '
        self.text = "%s%s" % (state, w.name if w and w.name else " ")
        self.bar.draw()
