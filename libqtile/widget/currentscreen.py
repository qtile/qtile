# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Alexander Fasching
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

from . import base
from .. import bar, hook


class CurrentScreen(base._TextBox):
    """
        Indicates whether the screen this widget is on is currently active
        or not.
    """

    defaults = [
        ('active_text', 'A', 'Text displayed when the screen is active'),
        ('inactive_text', 'I', 'Text displayed when the screen is inactive'),
        ('active_color', '00ff00', 'Color when screen is active'),
        ('inactive_color', 'ff0000', 'Color when screen is inactive')
    ]
    orientations = base.ORIENTATION_HORIZONTAL

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(CurrentScreen.defaults)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        if qtile.currentScreen == bar.screen:
            self.text = self.active_text
            self.foreground = self.active_color
        else:
            self.text = self.inactive_text
            self.foreground = self.inactive_color

        self.setup_hooks()

    def setup_hooks(self):
        def hook_response():
            if self.qtile.currentScreen == self.bar.screen:
                self.text = self.active_text
                self.foreground = self.active_color
            else:
                self.text = self.inactive_text
                self.foreground = self.inactive_color
            self.bar.draw()

        hook.subscribe.current_screen_change(hook_response)

