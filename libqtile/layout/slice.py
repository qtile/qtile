# -*- coding: utf-8 -*-
"""
Slice layout. Serves as example of delegating layouts (or sublayouts)
"""

from base import Layout, SingleWindow, Delegate
from max import Max
from .. import manager


class Single(SingleWindow):
    """Layout with single window

    Just like Max but asserts that window is the one
    """

    def __init__(self):
        SingleWindow.__init__(self)
        self.window = None

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


class Slice(Delegate):
    """Slice layout

    This layout cuts piece of screen and places a single window on that piece,
    and delegates other window placement to other layout
    """

    defaults = manager.Defaults(
        ("width", 256, "Slice width"),
        ("side", "left", "Side of the slice (left, right, top, bottom)"),
        ("name", "max", "Name of this layout."),
        )

    def __init__(self, side, width,
                 wname=None, wmclass=None, role=None,
                 fallback=Max(), **config):
        self.match = {
            'wname': wname,
            'wmclass': wmclass,
            'role': role,
            }
        Delegate.__init__(self, width=width, side=side, **config)
        self._slice = Single()
        self._fallback = fallback

    def clone(self, group):
        res = Layout.clone(self, group)
        res._slice = self._slice.clone(group)
        res._fallback = self._fallback.clone(group)
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
        self.delegate_layout(windows, {
            self._slice: win,
            self._fallback: sub,
            })

    def configure(self, win, screen):
        raise NotImplementedError("Should not be called")

    def _get_layouts(self):
        return self._slice, self._fallback

    def _get_active_layout(self):
        return self._fallback  # always

    def add(self, win):
        if self._slice.empty() and win.match(**self.match):
            self._slice.add(win)
            self.layouts[win] = self._slice
        else:
            self._fallback.add(win)
            self.layouts[win] = self._fallback

