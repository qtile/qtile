# -*- coding: utf-8 -*-
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2015 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
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

"""
Slice layout. Serves as example of delegating layouts (or sublayouts)
"""

from .base import Delegate, Layout, SingleWindow
from .max import Max


class Single(SingleWindow):
    """Layout with single window

    Just like Max but asserts that window is the one
    """

    def __init__(self):
        SingleWindow.__init__(self)
        self.window = None
        self.focused = False

    def add(self, window):
        assert self.window is None
        self.window = window

    def remove(self, window):
        assert self.window is window
        self.window = None

    def _get_window(self):
        return self.window

    def empty(self):
        """Is the layout empty

        Returns True if the layout empty (and is willing to accept windows)
        """
        return self.window is None

    def focus_first(self):
        self.focused = True
        return self.window

    def focus_last(self):
        self.focused = True
        return self.window

    def focus_next(self, window):
        if self.focused:
            self.focused = False
            return None
        return self.window

    def focus_previous(self, window):
        if self.focused:
            self.focused = False
            return None
        return self.window

    def cmd_next(self):
        pass

    def cmd_previous(self):
        pass


class Slice(Delegate):
    """Slice layout

    This layout cuts piece of screen and places a single window on that piece,
    and delegates other window placement to other layout
    """

    defaults = [
        ("width", 256, "Slice width"),
        ("side", "left", "Side of the slice (left, right, top, bottom)"),
        ("name", "max", "Name of this layout."),
        ("wname", None, "WM_NAME to match"),
        ("wmclass", None, "WM_CLASS to match"),
        ("role", None, "WM_WINDOW_ROLE to match"),
        ("fallback", Max(), "Fallback layout"),
    ]

    def __init__(self, **config):
        Delegate.__init__(self, **config)
        self.add_defaults(Slice.defaults)
        self.match = {
            'wname': self.wname,
            'wmclass': self.wmclass,
            'role': self.role,
        }
        self._slice = Single()

    def clone(self, group):
        res = Layout.clone(self, group)
        res._slice = self._slice.clone(group)
        res.fallback = self.fallback.clone(group)
        res._window = None
        return res

    def layout(self, windows, screen):
        if self.side == 'left':
            win, sub = screen.hsplit(self.width)
        elif self.side == 'right':
            sub, win = screen.hsplit(screen.width - self.width)
        elif self.side == 'top':
            win, sub = screen.vsplit(self.width)
        elif self.side == 'bottom':
            sub, win = screen.vsplit(screen.height - self.width)
        else:
            raise NotImplementedError(self.side)
        self.delegate_layout(
            windows,
            {
                self._slice: win,
                self.fallback: sub,
            }
        )

    def configure(self, win, screen):
        raise NotImplementedError("Should not be called")

    def _get_layouts(self):
        return (self._slice, self.fallback)

    def _get_active_layout(self):
        return self.fallback  # always

    def add(self, win):
        if self._slice.empty() and win.match(**self.match):
            self._slice.add(win)
            self.layouts[win] = self._slice
        else:
            self.fallback.add(win)
            self.layouts[win] = self.fallback

    def cmd_next(self):
        self.fallback.cmd_next()

    def cmd_previous(self):
        self.fallback.cmd_previous()
