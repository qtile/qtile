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
from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile.backend.base import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout.base import Layout
from libqtile.layout.max import Max

if TYPE_CHECKING:
    from typing import Any, Self, Sequence

    from libqtile.group import _Group


class Single(Layout):
    """Layout with single window

    Just like Max but asserts that window is the one
    """

    def __init__(self):
        Layout.__init__(self)
        self.window = None
        self.focused = False

    def add_client(self, window):
        assert self.window is None
        self.window = window

    def remove(self, window: Window) -> None:
        if self.window is not window:
            raise ValueError("Cannot remove, window not managed by layout")
        self.window = None

    def configure(self, window, screen_rect):
        if window is self.window:
            window.place(
                screen_rect.x,
                screen_rect.y,
                screen_rect.width,
                screen_rect.height,
                0,
                None,
            )
            window.unhide()
        else:
            window.hide()

    def empty(self):
        """Is the layout empty

        Returns True if the layout empty (and is willing to accept windows)
        """
        return self.window is None

    def focus_first(self) -> Window | None:
        self.focused = True
        return self.window

    def focus_last(self) -> Window | None:
        self.focused = True
        return self.window

    def focus_next(self, window: Window) -> Window | None:
        if self.focused:
            self.focused = False
            return None
        return self.window

    def focus_previous(self, window: Window) -> Window | None:
        if self.focused:
            self.focused = False
            return None
        return self.window

    def next(self) -> None:
        pass

    def previous(self) -> None:
        pass

    def get_windows(self):
        return self.window

    def info(self) -> dict[str, Any]:
        d = Layout.info(self)
        d["window"] = self.window.name if self.window else ""
        return d


class Slice(Layout):
    """Slice layout

    This layout cuts piece of screen_rect and places a single window on that
    piece, and delegates other window placement to other layout
    """

    defaults = [
        ("width", 256, "Slice width."),
        ("side", "left", "Position of the slice (left, right, top, bottom)."),
        ("match", None, "Match-object describing which window(s) to move to the slice."),
        ("fallback", Max(), "Layout to be used for the non-slice area."),
    ]

    fallback: Layout

    def __init__(self, **config):
        self.layouts = {}
        Layout.__init__(self, **config)
        self.add_defaults(Slice.defaults)
        self._slice = Single()

    def clone(self, group: _Group) -> Self:
        res = Layout.clone(self, group)
        res._slice = self._slice.clone(group)
        res.fallback = self.fallback.clone(group)
        return res

    def delegate_layout(self, windows, mapping):
        """Delegates layouting actual windows

        Parameters
        ===========
        windows:
            windows to layout
        mapping:
            mapping from layout to ScreenRect for each layout
        """
        grouped = {}
        for w in windows:
            lay = self.layouts[w]
            if lay in grouped:
                grouped[lay].append(w)
            else:
                grouped[lay] = [w]
        for lay, wins in grouped.items():
            lay.layout(wins, mapping[lay])

    def layout(self, windows: Sequence[Window], screen_rect: ScreenRect) -> None:
        win, sub = self._get_screen_rects(screen_rect)
        self.delegate_layout(
            windows,
            {
                self._slice: win,
                self.fallback: sub,
            },
        )

    def show(self, screen_rect: ScreenRect) -> None:
        win, sub = self._get_screen_rects(screen_rect)
        self._slice.show(win)
        self.fallback.show(sub)

    def configure(self, win, screen_rect):
        raise NotImplementedError("Should not be called")

    def _get_layouts(self):
        return (self._slice, self.fallback)

    def _get_active_layout(self):
        return self.fallback  # always

    def _get_screen_rects(self, screen):
        if self.side == "left":
            win, sub = screen.hsplit(self.width)
        elif self.side == "right":
            sub, win = screen.hsplit(screen.width - self.width)
        elif self.side == "top":
            win, sub = screen.vsplit(self.width)
        elif self.side == "bottom":
            sub, win = screen.vsplit(screen.height - self.width)
        else:
            raise NotImplementedError(self.side)
        return (win, sub)

    def add_client(self, win):
        if self._slice.empty() and self.match and self.match.compare(win):
            self._slice.add_client(win)
            self.layouts[win] = self._slice
        else:
            self.fallback.add_client(win)
            self.layouts[win] = self.fallback

    def remove(self, win: Window) -> Window:
        lay = self.layouts.pop(win)
        focus = lay.remove(win)
        if not focus:
            layouts = self._get_layouts()
            idx = layouts.index(lay)
            while idx < len(layouts) - 1 and not focus:
                idx += 1
                focus = layouts[idx].focus_first()
        return focus

    def hide(self) -> None:
        for lay in self._get_layouts():
            lay.hide()

    def focus(self, win):
        self.layouts[win].focus(win)

    def blur(self) -> None:
        for lay in self._get_layouts():
            lay.blur()

    def focus_first(self) -> Window | None:
        layouts = self._get_layouts()
        for lay in layouts:
            win = lay.focus_first()
            if win:
                return win
        return None

    def focus_last(self) -> None:
        layouts = self._get_layouts()
        for lay in reversed(layouts):
            win = lay.focus_last()
            if win:
                return win
        return None

    def focus_next(self, win: Window) -> Window | None:
        layouts = self._get_layouts()
        cur = self.layouts[win]
        focus = cur.focus_next(win)
        if not focus:
            idx = layouts.index(cur)
            while idx < len(layouts) - 1 and not focus:
                idx += 1
                focus = layouts[idx].focus_first()
        return focus

    def focus_previous(self, win: Window) -> Window | None:
        layouts = self._get_layouts()
        cur = self.layouts[win]
        focus = cur.focus_previous(win)
        if not focus:
            idx = layouts.index(cur)
            while idx > 0 and not focus:
                idx -= 1
                focus = layouts[idx].focus_last()
        return focus

    def __getattr__(self, name):
        """Delegate unimplemented command calls to active layout.

        For exposed commands that don't exist on the Slice class, this looks
        for an implementation on the active layout.
        """
        if "fallback" in self.__dict__:
            cmd = self.command(name)
            if cmd:
                return cmd
        return super().__getattr__(name)

    @expose_command()
    def next(self) -> None:
        self.fallback.next()

    @expose_command()
    def previous(self) -> None:
        self.fallback.previous()

    @expose_command()
    def commands(self):
        cmds = self._get_active_layout().commands()
        cmds.extend(cmd for cmd in Layout.commands(self) if cmd not in cmds)
        return cmds

    def get_windows(self):
        clients = list()
        for layout in self._get_layouts():
            if layout.get_windows() is not None:
                clients.extend(layout.get_windows())
        return clients

    def command(self, name: str):
        if name in self._commands:
            return self._commands.get(name)

        elif name in self._get_active_layout()._commands:
            return getattr(self._get_active_layout(), name)

    @expose_command()
    def move_to_slice(self):
        """Moves the current window to the slice."""
        win = self.group.current_window
        old_slice = self._slice.window
        if old_slice:
            self._slice.remove(old_slice)
            self.fallback.add_client(old_slice)
            self.layouts[old_slice] = self.fallback
        self.fallback.remove(win)
        self._slice.add_client(win)
        self.layouts[win] = self._slice
        self.group.layout_all()

    @expose_command()
    def info(self) -> dict[str, Any]:
        d = Layout.info(self)
        for layout in self._get_layouts():
            d[layout.name] = layout.info()
        return d
