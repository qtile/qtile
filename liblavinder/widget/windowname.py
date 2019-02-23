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
    """Displays the name of the window that currently has focus"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('show_state', True, 'show window status before window name'),
        ('for_current_screen', False, 'instead of this bars screen use currently active screen')
    ]

    def __init__(self, width=bar.STRETCH, **config):
        base._TextBox.__init__(self, width=width, **config)
        self.add_defaults(WindowName.defaults)

    def _configure(self, lavinder, bar):
        base._TextBox._configure(self, lavinder, bar)
        hook.subscribe.client_name_updated(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)

        @hook.subscribe.current_screen_change
        def on_screen_changed():
            if self.for_current_screen:
                self.update()

    def update(self, *args):
        if self.for_current_screen:
            w = self.lavinder.current_screen.group.current_window
        else:
            w = self.bar.screen.group.current_window
        state = ''
        if self.show_state and w is not None:
            if w.maximized:
                state = '[] '
            elif w.minimized:
                state = '_ '
            elif w.floating:
                state = 'V '
        self.text = "%s%s" % (state, w.name if w and w.name else " ")
        self.bar.draw()
