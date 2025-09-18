# Copyright (c) 2022 elParaguayo
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
from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile import hook
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect, _Match
from libqtile.layout import Columns, Max
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from libqtile.backend.base import Window
    from libqtile.group import _Group

    Rect = tuple[float, float, float, float]


class Split:
    def __init__(
        self, *, name: str, rect: Rect, layout: Layout, matches: list[_Match] = list()
    ) -> None:
        # Check that rect is correctly defined
        if not isinstance(rect, tuple | list):
            raise ValueError("Split rect should be a list/tuple.")

        if len(rect) != 4 or not all(isinstance(x, float | int) for x in rect):
            raise ValueError("Split rect should have 4 float/int members.")

        if isinstance(layout, ScreenSplit):
            raise ValueError("ScreenSplit layouts cannot be nested.")

        if matches:
            if isinstance(matches, list):
                if not all(isinstance(m, _Match) for m in matches):
                    raise ValueError("Invalid object in 'matches'.")
            else:
                raise ValueError("'matches' must be a list of 'Match' objects.")

        self.name = name
        self.rect = rect
        self.layout = layout
        self.matches = matches

    def clone(self, group) -> Split:
        return Split(
            name=self.name, rect=self.rect, layout=self.layout.clone(group), matches=self.matches
        )


class ScreenSplit(Layout):
    """
    A layout that allows you to split the screen into separate areas, each of which
    can be assigned its own layout.

    This layout is intended to be used on large monitors where separate layouts may be
    desirable. However, unlike creating virtual screens, this layout retains the full
    screen configuration meaning that full screen windows will continue to fill the entire
    screen.

    Each split is defined as a dictionary with the following keys:
      - ``name``: this is used with the ``ScreenSplit`` widget (see below)
      - ``rect``: a tuple of (x, y, width, height) with each value being between 0 and 1.
        These are relative values based on the screen's dimensions e.g. a value of
        ``(0.5, 0, 0.5, 1)`` would define an area starting at the top middle of the screen
        and extending to the bottom left corner.
      - ``layout``: the layout to occupy the defined split.
      - ``matches``: (optional) list of ``Match`` objects which define which windows will
        open in the defined split.

    Different splits can be selected by using the following ``lazy.layout.next_split()``
    and ``lazy.layout.previous_split()`` commands.

    To identify which split is active, users can use the ``ScreenSplit`` widget will show
    the name of the split and the relevant layout. Scrolling up and down on the widget will
    change the active split.

    .. note::

        While keybindings will be passed to the active split's layout, bindings using the
        ``.when(layout=...)``` syntax will not be applied as the primary layout is
        ``ScreenSplit``.
    """

    defaults = [
        (
            "splits",
            [
                {"name": "top", "rect": (0, 0, 1, 0.5), "layout": Max()},
                {"name": "bottom", "rect": (0, 0.5, 1, 0.5), "layout": Columns()},
            ],
            "Screen splits. See documentation for details.",
        )
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(ScreenSplit.defaults)
        self._split_index = 0
        self.layouts = {}
        self._move_win = None
        self._has_matches = None
        splits = []
        for s in self.splits:
            try:
                split_obj = Split(**s)
            except TypeError:
                raise ValueError("Splits must define 'name', 'rect' and 'layout'.")
            splits.append(split_obj)
        self.splits = splits
        self.hooks_set = False

    def _should_check(self, win):
        return win not in self.layouts and self._move_win is None

    @property
    def has_matches(self):
        if self._has_matches is None:
            self._has_matches = any(split.matches for split in self.splits)

        return self._has_matches

    @property
    def active_split(self):
        return self.splits[self._split_index]

    @active_split.setter
    def active_split(self, split):
        for i, sp in enumerate(self.splits):
            if sp == split:
                self._split_index = i
                hook.fire("layout_change", self, self.group)

    @property
    def active_layout(self):
        return self.active_split.layout

    @expose_command
    def commands(self):
        c = super().commands()
        c.extend(self.active_layout.commands())
        return c

    def command(self, name: str) -> Callable | None:
        if name in self._commands:
            return self._commands.get(name)

        elif name in self.active_split.layout._commands:
            return getattr(self.active_split.layout, name)

        return None

    def _get_rect(self, rect: Rect, screen: ScreenRect) -> ScreenRect:
        x, y, w, h = rect
        return ScreenRect(
            int(screen.x + x * screen.width),
            int(screen.y + y * screen.height),
            int(screen.width * w),
            int(screen.height * h),
            None,
        )

    def _set_hooks(self) -> None:
        if not self.hooks_set:
            hook.subscribe.focus_change(self.focus_split)
            self.hooks_set = True

    def _unset_hooks(self) -> None:
        if self.hooks_set:
            hook.unsubscribe.focus_change(self.focus_split)
            self.hooks_set = False

    def _match_win(self, win: Window) -> Split | None:
        for split in self.splits:
            if not split.matches:
                continue

            for m in split.matches:
                if win.match(m):
                    return split

        return None

    def clone(self, group: _Group) -> ScreenSplit:
        result = Layout.clone(self, group)
        new_splits = [split.clone(group) for split in self.splits]

        result.splits = new_splits
        return result

    def add_client(self, win: Window) -> None:
        split = None
        # If this is a new window and we're not moving this window between splits
        # then we should check for match rules
        if self.has_matches and self._should_check(win):
            split = self._match_win(win)

        if split is not None:
            self.active_split = split

        self.active_layout.add_client(win)
        self.layouts[win] = self.active_split

    def remove(self, win: Window) -> None:
        self.layouts[win].layout.remove(win)
        del self.layouts[win]

    def hide(self) -> None:
        self._unset_hooks()

    def show(self, _rect) -> None:
        self._set_hooks()

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        if client not in self.layouts:
            logger.warning("Unknown client: %s", client)
            return

        layout = self.layouts[client].layout
        rect = self._get_rect(self.layouts[client].rect, screen_rect)
        layout.configure(client, rect)

    def get_windows(self) -> list[Window]:
        return self.active_layout.get_windows()

    def _change_split(self, step: int = 1) -> None:
        self._split_index = (self._split_index + step) % len(self.splits)

    def _move_win_to_split(self, step: int = 1) -> None:
        # We get the ID of the next split now as removing window from a group
        # will shift focus to another window which could change the active
        # split.
        next_split = (self._split_index + step) % len(self.splits)
        self._move_win = self.group.current_window
        self.group.remove(self._move_win)
        self._split_index = next_split
        self.group.add(self._move_win)
        self.layouts[self._move_win] = self.active_split
        self._move_win = None
        hook.fire("layout_change", self, self.group)

    @expose_command
    def next(self) -> None:
        """Move to next client."""
        self.__getattr__("next")

    @expose_command
    def previous(self) -> None:
        """Move to previous client."""
        self.__getattr__("previous")

    def focus_first(self) -> Window:
        return self.active_layout.focus_first()

    def focus_last(self) -> Window:
        return self.active_layout.focus_last()

    def focus_next(self, win: Window) -> Window:
        return self.active_layout.focus_next(win)

    def focus_previous(self, win: Window) -> Window:
        return self.active_layout.focus_previous(win)

    def focus_split(self, win: Window | None = None) -> None:
        if win is None:
            win = self.group.current_window

        for split in self.splits:
            if win in split.layout.get_windows():
                if split is not self.active_split:
                    self.active_split = split
                    hook.fire("layout_change", self, self.group)
                break

    def focus(self, client: Window) -> None:
        self.focus_split(client)
        self.active_layout.focus(client)

    @expose_command
    def next_split(self) -> None:
        """Move to next split."""
        self._change_split()
        hook.fire("layout_change", self, self.group)

    @expose_command
    def previous_split(self) -> None:
        """Move to previous client."""
        self._change_split(-1)
        hook.fire("layout_change", self, self.group)

    @expose_command
    def move_window_to_next_split(self) -> None:
        """Move current window to next split."""
        self._move_win_to_split()

    @expose_command
    def move_window_to_previous_split(self) -> None:
        """Move current window to previous split."""
        self._move_win_to_split(-1)

    @expose_command
    def info(self) -> dict[str, Any]:
        inf = Layout.info(self)

        inf["current_split"] = self.active_split.name
        inf["current_layout"] = self.active_layout.name
        inf["current_clients"] = []
        inf["clients"] = []
        inf["splits"] = []

        for split in self.splits:
            clients = split.layout.info()["clients"]
            s_info = {
                "name": split.name,
                "rect": split.rect,
                "layout": split.layout.name,
                "clients": clients,
            }

            inf["splits"].append(s_info)
            inf["clients"].extend(clients)

            if split is self.active_split:
                inf["current_clients"] = clients

        return inf
