# -*- coding: utf-8 -*-
"""
Slice layout. Serves as example of delegating layouts (or sublayouts)
"""

from base import Layout, SingleWindow, Delegate
from ..config import Match
from max import Max

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

    def focus_first(self):
        return self.window

    def focus_last(self):
        return self.window

    def focus_next(self, window):
        return self.window

    def focus_previous(self, window):
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
        ("name", "slice", "Name of this layout."),
        ("side", "left", "Side of the slice (left, right, top, bottom)"),
        ("width", 256, "Slice width"),
        ("match", Match(title=['slice']), "Match object."
         "A window matching will be put into the slice."),
        ("fallback", Max(), "Layout to insert the other windows into."),
    ]

    def __init__(self, **config):
        Delegate.__init__(self, **config)
        self.add_defaults(Slice.defaults)
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
        if self._slice.empty() and self.match.compare(win):
            self._slice.add(win)
            self.layouts[win] = self._slice
        else:
            self.fallback.add(win)
            self.layouts[win] = self.fallback

    def cmd_next(self):
        self.fallback.cmd_next()

    def cmd_previous(self):
        self.fallback.cmd_previous()
