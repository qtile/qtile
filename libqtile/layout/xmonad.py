# Copyright (c) 2011-2012 Dustin Lacewell
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012 Maximilian Köhl
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 jpic
# Copyright (c) 2013 babadoo
# Copyright (c) 2013 Jure Ham
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Florian Scherf
# Copyright (c) 2017 Dirk Hartmann
# Copyright (c) 2024 Marco Paganini (auto_maximization code).
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

import math
from collections import namedtuple
from typing import TYPE_CHECKING

from libqtile.command.base import expose_command
from libqtile.layout.base import _SimpleLayoutBase

if TYPE_CHECKING:
    from typing import Any, Self

    from libqtile.backend.base import Window
    from libqtile.config import ScreenRect
    from libqtile.group import _Group


class MonadTall(_SimpleLayoutBase):
    """Emulate the behavior of XMonad's default tiling scheme.

    Main-Pane:

    A main pane that contains a single window takes up a vertical portion of
    the screen_rect based on the ratio setting. This ratio can be adjusted with
    the ``grow_main`` and ``shrink_main`` or, while the main pane is in
    focus, ``grow`` and ``shrink``. You may also set the ratio directly
    with ``set_ratio``.

    ::

        ---------------------
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        ---------------------

    Using the ``flip`` method will switch which horizontal side the main
    pane will occupy. The main pane is considered the "top" of the stack.

    ::

        ---------------------
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        ---------------------

    Secondary-panes:

    Occupying the rest of the screen_rect are one or more secondary panes.  The
    secondary panes will share the vertical space of the screen_rect however
    they can be resized at will with the ``grow`` and ``shrink``
    methods.  The other secondary panes will adjust their sizes to smoothly fill
    all of the space.

    ::

        ---------------------          ---------------------
        |            |      |          |            |______|
        |            |______|          |            |      |
        |            |      |          |            |      |
        |            |______|          |            |      |
        |            |      |          |            |______|
        |            |      |          |            |      |
        ---------------------          ---------------------

    Panes can be moved with the ``shuffle_up`` and ``shuffle_down``
    methods. As mentioned the main pane is considered the top of the stack;
    moving up is counter-clockwise and moving down is clockwise.

    ::

        ---------------------          ---------------------
        |            |      |          |            |      |
        |            |______|          |            |Focus |
        |            |      |          |            |      |
        |            |______|          |            |______|
        |            |      |          |            |______|
        |            |      |          |            |      |
        ---------------------          ---------------------

    Setting ``auto_maximize`` will cause the focused secondary pane to be
    automatically maximized on focus. The non-maximized panes will shrink to
    the height specified by ``min_secondary_size``.

    The opposite is true if the layout is "flipped".

    ::

        ---------------------          ---------------------
        |            |  2   |          |   2   |           |
        |            |______|          |_______|           |
        |            |  3   |          |   3   |           |
        |     1      |______|          |_______|     1     |
        |            |  4   |          |   4   |           |
        |            |      |          |       |           |
        ---------------------          ---------------------


    Normalizing/Resetting:

    To restore all secondary client windows to their default size ratios
    use the ``normalize`` method.

    To reset all client windows to their default sizes, including the primary
    window, use the ``reset`` method.

    Maximizing:

    To toggle a client window between its minimum and maximum sizes
    simply use the ``maximize`` on a focused client.

    Suggested Bindings::

        Key([modkey], "h", lazy.layout.left()),
        Key([modkey], "l", lazy.layout.right()),
        Key([modkey], "j", lazy.layout.down()),
        Key([modkey], "k", lazy.layout.up()),
        Key([modkey, "shift"], "h", lazy.layout.swap_left()),
        Key([modkey, "shift"], "l", lazy.layout.swap_right()),
        Key([modkey, "shift"], "j", lazy.layout.shuffle_down()),
        Key([modkey, "shift"], "k", lazy.layout.shuffle_up()),
        Key([modkey], "i", lazy.layout.grow()),
        Key([modkey], "m", lazy.layout.shrink()),
        Key([modkey], "n", lazy.layout.reset()),
        Key([modkey, "shift"], "n", lazy.layout.normalize()),
        Key([modkey], "o", lazy.layout.maximize()),
        Key([modkey, "shift"], "s", lazy.layout.toggle_auto_maximize()),
        Key([modkey, "shift"], "space", lazy.layout.flip()),
    """

    _left = 0
    _right = 1

    defaults = [
        ("auto_maximize", False, "Maximize secondary windows on focus."),
        ("border_focus", "#ff0000", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        ("border_width", 2, "Border width."),
        ("single_border_width", None, "Border width for single window"),
        ("single_margin", None, "Margin size for single window"),
        ("margin", 0, "Margin of the layout"),
        (
            "ratio",
            0.5,
            "The percent of the screen-space the master pane should occupy by default.",
        ),
        (
            "min_ratio",
            0.25,
            "The percent of the screen-space the master pane should occupy at minimum.",
        ),
        (
            "max_ratio",
            0.75,
            "The percent of the screen-space the master pane should occupy at maximum.",
        ),
        ("min_secondary_size", 85, "minimum size in pixel for a secondary pane window "),
        (
            "align",
            _left,
            "Which side master plane will be placed "
            "(one of ``MonadTall._left`` or ``MonadTall._right``)",
        ),
        ("change_ratio", 0.05, "Resize ratio"),
        ("change_size", 20, "Resize change in pixels"),
        (
            "new_client_position",
            "after_current",
            "Place new windows: "
            " after_current - after the active window."
            " before_current - before the active window,"
            " top - at the top of the stack,"
            " bottom - at the bottom of the stack,",
        ),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(MonadTall.defaults)
        if self.single_border_width is None:
            self.single_border_width = self.border_width
        if self.single_margin is None:
            self.single_margin = self.margin
        self.relative_sizes = []
        self._screen_rect = None
        self.default_ratio = self.ratio

    # screen_rect is a property as the MonadThreeCol layout needs to perform
    # additional actions when the attribute is modified
    @property
    def screen_rect(self):
        return self._screen_rect

    @screen_rect.setter
    def screen_rect(self, value):
        self._screen_rect = value

    @property
    def focused(self):
        return self.clients.current_index

    def _get_relative_size_from_absolute(self, absolute_size):
        return absolute_size / self.screen_rect.height

    def _get_absolute_size_from_relative(self, relative_size):
        return int(relative_size * self.screen_rect.height)

    def clone(self, group: _Group) -> Self:
        "Clone layout for other groups"
        c = _SimpleLayoutBase.clone(self, group)
        c.relative_sizes = []
        c.screen_rect = group.screen.get_rect() if group.screen else None
        c.ratio = self.ratio
        c.align = self.align
        return c

    def add_client(self, client: Window) -> None:  # type: ignore[override]
        "Add client to layout"
        self.clients.add_client(client, client_position=self.new_client_position)
        self.do_normalize = True

    def focus(self, client):
        super().focus(client)
        # Only maximize the window in the secondary pane when focus is *not* in
        # the main pane. Doing so in the main pane causes the last secondary
        # window to always be in focus when switching from secondary -> main.
        if self.focused != 0:
            self._maximize_focused_secondary()

    def remove(self, client: Window) -> Window | None:
        "Remove client from layout"
        p = super().remove(client)
        self.do_normalize = True
        # When auto_maximize is set and the user closes the first (topmost)
        # secondary window, focus goes back to the main window. In this case,
        # we WANT to force redraw of the windows in the secondary pane so we
        # get a maximized topmost window again.
        if self.auto_maximize and self.focused == 0 and len(self.clients) > 2:
            # This will also trigger secondary maximization, if needed.
            self.focus(self.clients[1])
        return p

    @expose_command()
    def set_ratio(self, ratio):
        "Directly set the main pane ratio"
        ratio = min(self.max_ratio, ratio)
        self.ratio = max(self.min_ratio, ratio)
        self.group.layout_all()

    @expose_command()
    def normalize(self, redraw=True):
        "Evenly distribute screen-space among secondary clients"
        n = len(self.clients) - 1  # exclude main client, 0
        # if secondary clients exist
        if n > 0 and self.screen_rect is not None:
            self.relative_sizes = [1.0 / n] * n
        # reset main pane ratio
        if redraw:
            self.group.layout_all()
        self.do_normalize = False

    @expose_command()
    def reset(self, ratio=None, redraw=True):
        "Reset Layout."
        self.ratio = ratio or self.default_ratio
        if self.align == self._right:
            self.align = self._left
        self.normalize(redraw)

    @expose_command()
    def toggle_auto_maximize(self):
        "Toggle auto maximize secondary window on focus."
        self.auto_maximize = not self.auto_maximize
        self.normalize(True)
        if self.focused != 0:
            self._maximize_focused_secondary()

    def _maximize_main(self):
        "Toggle the main pane between min and max size"
        if self.ratio <= 0.5 * (self.max_ratio + self.min_ratio):
            self.ratio = self.max_ratio
        else:
            self.ratio = self.min_ratio
        self.group.layout_all()

    def _maximize_secondary(self):
        "Toggle the focused secondary pane between min and max size"
        n = len(self.clients) - 2  # total shrinking clients
        # total size of collapsed secondaries
        collapsed_size = self.min_secondary_size * n
        nidx = self.focused - 1  # focused size index
        # total height of maximized secondary
        maxed_size = self.group.screen.dheight - collapsed_size
        # if maximized or nearly maximized
        if (
            abs(self._get_absolute_size_from_relative(self.relative_sizes[nidx]) - maxed_size)
            < self.change_size
        ):
            # minimize
            self._shrink_secondary(
                self._get_absolute_size_from_relative(self.relative_sizes[nidx])
                - self.min_secondary_size
            )
        # otherwise maximize
        else:
            self._grow_secondary(maxed_size)

    def _maximize_focused_secondary(self):
        "Maximize the 'non-maximized' focused secondary pane"

        # Return immediately if no self.group.screen
        # (this may happen when moving windows across screens.)
        if self.group.screen is None:
            return

        # If auto_maximize is off, return immediately.
        if not self.auto_maximize:
            return

        # if we have 1 or 2 panes, do nothing.
        if len(self.clients) < 3:
            return

        # Recalculate relative_sizes
        self.normalize(redraw=False)
        if len(self.relative_sizes) == 0:
            return

        # If the focused window (self.focused) is 0 (main pane), adjust
        # focused to work directly on the secondary pane windows.
        focused = max(1, self.focused)

        n = len(self.clients) - 2  # total shrinking clients
        # total size of collapsed secondaries
        collapsed_size = self.min_secondary_size * n
        nidx = max(0, focused - 1)  # focused size index
        # total height of maximized secondary
        maxed_size = self.group.screen.dheight - collapsed_size

        # Maximize if window is not already maximized.
        if (
            abs(self._get_absolute_size_from_relative(self.relative_sizes[nidx]) - maxed_size)
            >= self.change_size
        ):
            self._grow_secondary(maxed_size)
            self.group.layout_all()

    @expose_command()
    def maximize(self):
        "Grow the currently focused client to the max size"
        # if we have 1 or 2 panes or main pane is focused
        if len(self.clients) < 3 or self.focused == 0:
            self._maximize_main()
        # secondary is focused
        else:
            self._maximize_secondary()
        self.group.layout_all()

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        "Position client based on order and sizes"
        self.screen_rect = screen_rect

        # if no sizes or normalize flag is set, normalize
        if not self.relative_sizes or self.do_normalize:
            self.normalize(False)

        # if client not in this layout
        if not self.clients or client not in self.clients:
            client.hide()
            return

        # determine focus border-color
        if client.has_focus:
            px = self.border_focus
        else:
            px = self.border_normal

        # single client - fullscreen
        if len(self.clients) == 1:
            client.place(
                self.screen_rect.x,
                self.screen_rect.y,
                self.screen_rect.width - 2 * self.single_border_width,
                self.screen_rect.height - 2 * self.single_border_width,
                self.single_border_width,
                px,
                margin=self.single_margin,
            )
            client.unhide()
            return
        cidx = self.clients.index(client)
        self._configure_specific(client, screen_rect, px, cidx)
        client.unhide()

    def _configure_specific(self, client, screen_rect, px, cidx):
        """Specific configuration for xmonad tall."""
        self.screen_rect = screen_rect

        # calculate main/secondary pane size
        width_main = int(self.screen_rect.width * self.ratio)
        width_shared = self.screen_rect.width - width_main

        # calculate client's x offset
        if self.align == self._left:  # left or up orientation
            if cidx == 0:
                # main client
                xpos = self.screen_rect.x
            else:
                # secondary client
                xpos = self.screen_rect.x + width_main
        else:  # right or down orientation
            if cidx == 0:
                # main client
                xpos = self.screen_rect.x + width_shared - self.margin
            else:
                # secondary client
                xpos = self.screen_rect.x

        # calculate client height and place
        if cidx > 0:
            # secondary client
            width = width_shared - 2 * self.border_width
            # ypos is the sum of all clients above it
            ypos = self.screen_rect.y + self._get_absolute_size_from_relative(
                sum(self.relative_sizes[: cidx - 1])
            )
            # get height from precalculated height list
            height = self._get_absolute_size_from_relative(self.relative_sizes[cidx - 1])
            # fix double margin
            if cidx > 1:
                ypos -= self.margin
                height += self.margin
            # place client based on calculated dimensions
            client.place(
                xpos,
                ypos,
                width,
                height - 2 * self.border_width,
                self.border_width,
                px,
                margin=self.margin,
            )
        else:
            # main client
            client.place(
                xpos,
                self.screen_rect.y,
                width_main,
                self.screen_rect.height,
                self.border_width,
                px,
                margin=[
                    self.margin,
                    2 * self.border_width,
                    self.margin + 2 * self.border_width,
                    self.margin,
                ],
            )

    @expose_command()
    def info(self) -> dict[str, Any]:
        d = _SimpleLayoutBase.info(self)
        d.update(
            dict(
                main=d["clients"][0] if self.clients else None,
                secondary=d["clients"][1::] if self.clients else [],
            )
        )
        return d

    def get_shrink_margin(self, cidx):
        "Return how many remaining pixels a client can shrink"
        return max(
            0,
            self._get_absolute_size_from_relative(self.relative_sizes[cidx])
            - self.min_secondary_size,
        )

    def _shrink(self, cidx, amt):
        """Reduce the size of a client

        Will only shrink the client until it reaches the configured minimum
        size. Any amount that was prevented in the resize is returned.
        """
        # get max resizable amount
        margin = self.get_shrink_margin(cidx)
        if amt > margin:  # too much
            self.relative_sizes[cidx] -= self._get_relative_size_from_absolute(margin)
            return amt - margin
        else:
            self.relative_sizes[cidx] -= self._get_relative_size_from_absolute(amt)
            return 0

    def shrink_up(self, cidx, amt):
        """Shrink the window up

        Will shrink all secondary clients above the specified index in order.
        Each client will attempt to shrink as much as it is able before the
        next client is resized.

        Any amount that was unable to be applied to the clients is returned.
        """
        left = amt  # track unused shrink amount
        # for each client before specified index
        for idx in range(cidx):
            # shrink by whatever is left-over of original amount
            left -= left - self._shrink(idx, left)
        # return unused shrink amount
        return left

    def shrink_up_shared(self, cidx, amt):
        """Shrink the shared space

        Will shrink all secondary clients above the specified index by an equal
        share of the provided amount. After applying the shared amount to all
        affected clients, any amount left over will be applied in a non-equal
        manner with ``shrink_up``.

        Any amount that was unable to be applied to the clients is returned.
        """
        # split shrink amount among number of clients
        per_amt = amt / cidx
        left = amt  # track unused shrink amount
        # for each client before specified index
        for idx in range(cidx):
            # shrink by equal amount and track left-over
            left -= per_amt - self._shrink(idx, per_amt)
        # apply non-equal shrinkage secondary pass
        # in order to use up any left over shrink amounts
        left = self.shrink_up(cidx, left)
        # return whatever could not be applied
        return left

    def shrink_down(self, cidx, amt):
        """Shrink current window down

        Will shrink all secondary clients below the specified index in order.
        Each client will attempt to shrink as much as it is able before the
        next client is resized.

        Any amount that was unable to be applied to the clients is returned.
        """
        left = amt  # track unused shrink amount
        # for each client after specified index
        for idx in range(cidx + 1, len(self.relative_sizes)):
            # shrink by current total left-over amount
            left -= left - self._shrink(idx, left)
        # return unused shrink amount
        return left

    def shrink_down_shared(self, cidx, amt):
        """Shrink secondary clients

        Will shrink all secondary clients below the specified index by an equal
        share of the provided amount. After applying the shared amount to all
        affected clients, any amount left over will be applied in a non-equal
        manner with ``shrink_down``.

        Any amount that was unable to be applied to the clients is returned.
        """
        # split shrink amount among number of clients
        per_amt = amt / (len(self.relative_sizes) - 1 - cidx)
        left = amt  # track unused shrink amount
        # for each client after specified index
        for idx in range(cidx + 1, len(self.relative_sizes)):
            # shrink by equal amount and track left-over
            left -= per_amt - self._shrink(idx, per_amt)
        # apply non-equal shrinkage secondary pass
        # in order to use up any left over shrink amounts
        left = self.shrink_down(cidx, left)
        # return whatever could not be applied
        return left

    def _grow_main(self, amt):
        """Will grow the client that is currently in the main pane"""
        self.ratio += amt
        self.ratio = min(self.max_ratio, self.ratio)

    def _grow_solo_secondary(self, amt):
        """Will grow the solitary client in the secondary pane"""
        self.ratio -= amt
        self.ratio = max(self.min_ratio, self.ratio)

    def _grow_secondary(self, amt):
        """Will grow the focused client in the secondary pane"""
        half_change_size = amt / 2
        # track unshrinkable amounts
        left = amt
        # first secondary (top)
        if self.focused == 1:
            # only shrink downwards
            left -= amt - self.shrink_down_shared(0, amt)
        # last secondary (bottom)
        elif self.focused == len(self.clients) - 1:
            # only shrink upwards
            left -= amt - self.shrink_up(len(self.relative_sizes) - 1, amt)
        # middle secondary
        else:
            # get size index
            idx = self.focused - 1
            # shrink up and down
            left -= half_change_size - self.shrink_up_shared(idx, half_change_size)
            left -= half_change_size - self.shrink_down_shared(idx, half_change_size)
            left -= half_change_size - self.shrink_up_shared(idx, half_change_size)
            left -= half_change_size - self.shrink_down_shared(idx, half_change_size)
        # calculate how much shrinkage took place
        diff = amt - left
        # grow client by diff amount
        self.relative_sizes[self.focused - 1] += self._get_relative_size_from_absolute(diff)

    @expose_command()
    def grow(self):
        """Grow current window

        Will grow the currently focused client reducing the size of those
        around it. Growing will stop when no other secondary clients can reduce
        their size any further.
        """
        if self.focused == 0:
            self._grow_main(self.change_ratio)
        elif len(self.clients) == 2:
            self._grow_solo_secondary(self.change_ratio)
        else:
            self._grow_secondary(self.change_size)
        self.group.layout_all()

    @expose_command()
    def grow_main(self):
        """Grow main pane

        Will grow the main pane, reducing the size of clients in the secondary
        pane.
        """
        self._grow_main(self.change_ratio)
        self.group.layout_all()

    @expose_command()
    def shrink_main(self):
        """Shrink main pane

        Will shrink the main pane, increasing the size of clients in the
        secondary pane.
        """
        self._shrink_main(self.change_ratio)
        self.group.layout_all()

    def _grow(self, cidx, amt):
        "Grow secondary client by specified amount"
        self.relative_sizes[cidx] += self._get_relative_size_from_absolute(amt)

    def grow_up_shared(self, cidx, amt):
        """Grow higher secondary clients

        Will grow all secondary clients above the specified index by an equal
        share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / cidx
        for idx in range(cidx):
            self._grow(idx, per_amt)

    def grow_down_shared(self, cidx, amt):
        """Grow lower secondary clients

        Will grow all secondary clients below the specified index by an equal
        share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / (len(self.relative_sizes) - 1 - cidx)
        for idx in range(cidx + 1, len(self.relative_sizes)):
            self._grow(idx, per_amt)

    def _shrink_main(self, amt):
        """Will shrink the client that currently in the main pane"""
        self.ratio -= amt
        self.ratio = max(self.min_ratio, self.ratio)

    def _shrink_solo_secondary(self, amt):
        """Will shrink the solitary client in the secondary pane"""
        self.ratio += amt
        self.ratio = min(self.max_ratio, self.ratio)

    def _shrink_secondary(self, amt):
        """Will shrink the focused client in the secondary pane"""
        # get focused client
        client = self.clients[self.focused]

        # get default change size
        change = amt

        # get left-over height after change
        left = client.height - amt
        # if change would violate min_secondary_size
        if left < self.min_secondary_size:
            # just reduce to min_secondary_size
            change = client.height - self.min_secondary_size

        # calculate half of that change
        half_change = change / 2

        # first secondary (top)
        if self.focused == 1:
            # only grow downwards
            self.grow_down_shared(0, change)
        # last secondary (bottom)
        elif self.focused == len(self.clients) - 1:
            # only grow upwards
            self.grow_up_shared(len(self.relative_sizes) - 1, change)
        # middle secondary
        else:
            idx = self.focused - 1
            # grow up and down
            self.grow_up_shared(idx, half_change)
            self.grow_down_shared(idx, half_change)
        # shrink client by total change
        self.relative_sizes[self.focused - 1] -= self._get_relative_size_from_absolute(change)

    @expose_command()
    def next(self) -> None:
        _SimpleLayoutBase.next(self)

    @expose_command()
    def previous(self) -> None:
        _SimpleLayoutBase.previous(self)

    @expose_command()
    def shrink(self):
        """Shrink current window

        Will shrink the currently focused client reducing the size of those
        around it. Shrinking will stop when the client has reached the minimum
        size.
        """
        if self.focused == 0:
            self._shrink_main(self.change_ratio)
        elif len(self.clients) == 2:
            self._shrink_solo_secondary(self.change_ratio)
        else:
            self._shrink_secondary(self.change_size)
        self.group.layout_all()

    @expose_command()
    def shuffle_up(self):
        """Shuffle the client up the stack"""
        self.clients.shuffle_up()
        self.group.layout_all()
        self.group.focus(self.clients.current_client)

    @expose_command()
    def shuffle_down(self):
        """Shuffle the client down the stack"""
        self.clients.shuffle_down()
        self.group.layout_all()
        self.group.focus(self.clients[self.focused])

    @expose_command()
    def flip(self):
        """Flip the layout horizontally"""
        self.align = self._left if self.align == self._right else self._right
        self.group.layout_all()

    def _get_closest(self, x, y, clients):
        """Get closest window to a point x,y"""
        target = min(
            clients,
            key=lambda c: math.hypot(c.x - x, c.y - y),
            default=self.clients.current_client,
        )
        return target

    @expose_command()
    def swap(self, window1: Window, window2: Window) -> None:
        """Swap two windows"""
        _SimpleLayoutBase.swap(self, window1, window2)

    @expose_command("shuffle_left")
    def swap_left(self):
        """Swap current window with closest window to the left"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["x"] < x]
        target = self._get_closest(x, y, candidates)
        self.swap(win, target)

    @expose_command("shuffle_right")
    def swap_right(self):
        """Swap current window with closest window to the right"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["x"] > x]
        target = self._get_closest(x, y, candidates)
        self.swap(win, target)

    @expose_command()
    def swap_main(self):
        """Swap current window to main pane"""
        if self.align == self._left:
            self.swap_left()
        elif self.align == self._right:
            self.swap_right()

    @expose_command()
    def left(self):
        """Focus on the closest window to the left of the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["x"] < x]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)

    @expose_command()
    def right(self):
        """Focus on the closest window to the right of the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["x"] > x]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)

    @expose_command()
    def up(self):
        """Focus on the closest window above the current window"""
        self.previous()

    @expose_command()
    def down(self):
        """Focus on the closest window below the current window"""
        self.next()


class MonadWide(MonadTall):
    """Emulate the behavior of XMonad's horizontal tiling scheme.

    This layout attempts to emulate the behavior of XMonad wide
    tiling scheme.

    Main-Pane:

    A main pane that contains a single window takes up a horizontal
    portion of the screen_rect based on the ratio setting. This ratio can be
    adjusted with the ``grow_main`` and ``shrink_main`` or,
    while the main pane is in focus, ``grow`` and ``shrink``.

    ::

        ---------------------
        |                   |
        |                   |
        |                   |
        |___________________|
        |                   |
        |                   |
        ---------------------

    Using the ``flip`` method will switch which vertical side the
    main pane will occupy. The main pane is considered the "top" of
    the stack.

    ::

        ---------------------
        |                   |
        |___________________|
        |                   |
        |                   |
        |                   |
        |                   |
        ---------------------

    Secondary-panes:

    Occupying the rest of the screen_rect are one or more secondary panes.
    The secondary panes will share the horizontal space of the screen_rect
    however they can be resized at will with the ``grow`` and
    ``shrink`` methods. The other secondary panes will adjust their
    sizes to smoothly fill all of the space.

    ::

        ---------------------          ---------------------
        |                   |          |                   |
        |                   |          |                   |
        |                   |          |                   |
        |___________________|          |___________________|
        |     |       |     |          |   |           |   |
        |     |       |     |          |   |           |   |
        ---------------------          ---------------------

    Panes can be moved with the ``shuffle_up`` and ``shuffle_down``
    methods. As mentioned the main pane is considered the top of the
    stack; moving up is counter-clockwise and moving down is clockwise.

    The opposite is true if the layout is "flipped".

    ::

        ---------------------          ---------------------
        |                   |          |  2  |   3   |  4  |
        |         1         |          |_____|_______|_____|
        |                   |          |                   |
        |___________________|          |                   |
        |     |       |     |          |        1          |
        |  2  |   3   |  4  |          |                   |
        ---------------------          ---------------------

    Normalizing/Resetting:

    To restore all secondary client windows to their default size ratios
    use the ``normalize`` method.

    To reset all client windows to their default sizes, including the primary
    window, use the ``reset`` method.


    Maximizing:

    To toggle a client window between its minimum and maximum sizes
    simply use the ``maximize`` on a focused client.

    Suggested Bindings::

        Key([modkey], "h", lazy.layout.left()),
        Key([modkey], "l", lazy.layout.right()),
        Key([modkey], "j", lazy.layout.down()),
        Key([modkey], "k", lazy.layout.up()),
        Key([modkey, "shift"], "h", lazy.layout.swap_left()),
        Key([modkey, "shift"], "l", lazy.layout.swap_right()),
        Key([modkey, "shift"], "j", lazy.layout.shuffle_down()),
        Key([modkey, "shift"], "k", lazy.layout.shuffle_up()),
        Key([modkey], "i", lazy.layout.grow()),
        Key([modkey], "m", lazy.layout.shrink()),
        Key([modkey], "n", lazy.layout.reset()),
        Key([modkey, "shift"], "n", lazy.layout.normalize()),
        Key([modkey], "o", lazy.layout.maximize()),
        Key([modkey, "shift"], "space", lazy.layout.flip()),
    """

    _up = 0
    _down = 1

    def _get_relative_size_from_absolute(self, absolute_size):
        return absolute_size / self.screen_rect.width

    def _get_absolute_size_from_relative(self, relative_size):
        return int(relative_size * self.screen_rect.width)

    def _maximize_secondary(self):
        """Toggle the focused secondary pane between min and max size."""
        n = len(self.clients) - 2  # total shrinking clients
        # total size of collapsed secondaries
        collapsed_size = self.min_secondary_size * n
        nidx = self.focused - 1  # focused size index
        # total width of maximized secondary
        maxed_size = self.screen_rect.width - collapsed_size
        # if maximized or nearly maximized
        if (
            abs(self._get_absolute_size_from_relative(self.relative_sizes[nidx]) - maxed_size)
            < self.change_size
        ):
            # minimize
            self._shrink_secondary(
                self._get_absolute_size_from_relative(self.relative_sizes[nidx])
                - self.min_secondary_size
            )
        # otherwise maximize
        else:
            self._grow_secondary(maxed_size)

    def _configure_specific(self, client, screen_rect, px, cidx):
        """Specific configuration for xmonad wide."""
        self.screen_rect = screen_rect

        # calculate main/secondary column widths
        height_main = int(self.screen_rect.height * self.ratio)
        height_shared = self.screen_rect.height - height_main

        # calculate client's x offset
        if self.align == self._up:  # up orientation
            if cidx == 0:
                # main client
                ypos = self.screen_rect.y
            else:
                # secondary client
                ypos = self.screen_rect.y + height_main
        else:  # right or down orientation
            if cidx == 0:
                # main client
                ypos = self.screen_rect.y + height_shared - self.margin
            else:
                # secondary client
                ypos = self.screen_rect.y

        # calculate client height and place
        if cidx > 0:
            # secondary client
            height = height_shared - 2 * self.border_width
            # xpos is the sum of all clients left of it
            xpos = self.screen_rect.x + self._get_absolute_size_from_relative(
                sum(self.relative_sizes[: cidx - 1])
            )
            # get width from precalculated width list
            width = self._get_absolute_size_from_relative(self.relative_sizes[cidx - 1])
            # fix double margin
            if cidx > 1:
                xpos -= self.margin
                width += self.margin
            # place client based on calculated dimensions
            client.place(
                xpos,
                ypos,
                width - 2 * self.border_width,
                height,
                self.border_width,
                px,
                margin=self.margin,
            )
        else:
            # main client
            client.place(
                self.screen_rect.x,
                ypos,
                self.screen_rect.width,
                height_main,
                self.border_width,
                px,
                margin=[
                    self.margin,
                    self.margin + 2 * self.border_width,
                    2 * self.border_width,
                    self.margin,
                ],
            )

    def _shrink_secondary(self, amt):
        """Will shrink the focused client in the secondary pane"""
        # get focused client
        client = self.clients[self.focused]

        # get default change size
        change = amt

        # get left-over height after change
        left = client.width - amt
        # if change would violate min_secondary_size
        if left < self.min_secondary_size:
            # just reduce to min_secondary_size
            change = client.width - self.min_secondary_size

        # calculate half of that change
        half_change = change / 2

        # first secondary (top)
        if self.focused == 1:
            # only grow downwards
            self.grow_down_shared(0, change)
        # last secondary (bottom)
        elif self.focused == len(self.clients) - 1:
            # only grow upwards
            self.grow_up_shared(len(self.relative_sizes) - 1, change)
        # middle secondary
        else:
            idx = self.focused - 1
            # grow up and down
            self.grow_up_shared(idx, half_change)
            self.grow_down_shared(idx, half_change)
        # shrink client by total change
        self.relative_sizes[self.focused - 1] -= self._get_relative_size_from_absolute(change)

    @expose_command()
    def swap_left(self):
        """Swap current window with closest window to the down"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients.clients if c.info()["y"] > y]
        target = self._get_closest(x, y, candidates)
        self.swap(win, target)

    @expose_command()
    def swap_right(self):
        """Swap current window with closest window to the up"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["y"] < y]
        target = self._get_closest(x, y, candidates)
        self.swap(win, target)

    @expose_command()
    def swap_main(self):
        """Swap current window to main pane"""
        if self.align == self._up:
            self.swap_right()
        elif self.align == self._down:
            self.swap_left()

    @expose_command()
    def left(self):
        """Focus on the closest window to the left of the current window"""
        self.previous()

    @expose_command()
    def right(self):
        """Focus on the closest window to the right of the current window"""
        self.next()

    @expose_command()
    def up(self):
        """Focus on the closest window above the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["y"] < y]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)

    @expose_command()
    def down(self):
        """Focus on the closest window below the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()["y"] > y]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)


class MonadThreeCol(MonadTall):
    """Emulate the behavior of XMonad's ThreeColumns layout.

    A layout similar to tall but with three columns. With an ultra wide display
    this layout can be used for a huge main window - ideally at the center of the
    screen - and up to six reasonable sized secondary windows.

    Main-Pane:

    A main pane that contains a single window takes up a vertical portion of
    the screen_rect based on the ratio setting. This ratio can be adjusted with
    the ``grow_main`` and ``shrink_main`` or, while the main pane is in
    focus, ``grow`` and ``shrink``. The main pane can also be centered.

    ::

        ---------------------------    ---------------------------
        |           |      |      |    |      |           |      |
        |           |      |      |    |      |           |      |
        |           |      |      |    |      |           |      |
        |           |      |      |    |      |           |      |
        |           |      |      |    |      |           |      |
        |           |      |      |    |      |           |      |
        ---------------------------    ---------------------------

    Secondary-panes:

    Occupying the rest of the screen_rect are one or more secondary panes.  The
    secondary panes will be divided into two columns and share the vertical space
    of each column. However they can be resized at will with the ``grow`` and
    ``shrink`` methods. The other secondary panes will adjust their sizes to
    smoothly fill all of the space.

    ::

        ---------------------------    ---------------------------
        |           |      |      |    |           |______|      |
        |           |______|      |    |           |      |      |
        |           |      |______|    |           |      |______|
        |           |______|      |    |           |      |      |
        |           |      |      |    |           |______|      |
        |           |      |      |    |           |      |      |
        ---------------------------    ---------------------------

    Panes can be moved with the ``shuffle_up`` and ``shuffle_down``
    methods. As mentioned the main pane is considered the top of the stack;
    moving up is counter-clockwise and moving down is clockwise. A secondary
    pane can also be promoted to the main pane with the ``swap_main``
    method.

    Normalizing/Resetting:

    To restore all secondary client windows to their default size ratios
    use the ``normalize`` method.

    To reset all client windows to their default sizes, including the primary
    window, use the ``reset`` method.

    Maximizing:

    To maximized a client window simply use the ``maximize`` on a focused
    client.
    """

    defaults = [
        ("main_centered", True, "Place the main pane at the center of the screen"),
        (
            "new_client_position",
            "top",
            "Place new windows: "
            " after_current - after the active window."
            " before_current - before the active window,"
            " top - at the top of the stack,"
            " bottom - at the bottom of the stack,",
        ),
    ]

    __column = namedtuple("__column", "name count start end")

    def __init__(self, **config):
        MonadTall.__init__(self, **config)
        self.add_defaults(MonadThreeCol.defaults)

    # mypy doesn't like the setter when the getter isn't present
    # see https://github.com/python/mypy/issues/5936
    @MonadTall.screen_rect.setter  # type: ignore[attr-defined]
    def screen_rect(self, value):
        # If the screen_rect size has change then we need to normalise secondary
        # windows so they're resized to fill the new space correctly
        if value != self._screen_rect:
            self.do_normalize = True
        self._screen_rect = value

    def _configure_specific(self, client, screen_rect, border_color, index):
        """Specific configuration for xmonad three columns."""
        if index == 0:
            self._configure_main(client)
        elif self._get_column(index - 1).name == "left":
            self._configure_left(client, index)
        else:
            self._configure_right(client, index)

    def _configure_main(self, client):
        """Configure the main client"""
        width = self._get_main_width()
        height = self.screen_rect.height
        left = self.screen_rect.x
        top = self.screen_rect.y

        if self.main_centered and len(self.clients) > 2:
            left += (self.screen_rect.width - width) // 2

        self._place_client(client, left, top, width, height)

    def _configure_left(self, client, index):
        """Configure the left column"""
        width = self._get_secondary_widths()[0]
        height = self._get_secondary_height(index)
        left = self.screen_rect.x
        top = self.screen_rect.y + self._get_relative_sizes_above(index)

        if not self.main_centered or len(self.clients) == 2:
            left += self._get_main_width()

        self._place_client(client, left, top, width, height)

    def _configure_right(self, client, index):
        """Configure the right column"""
        widths = self._get_secondary_widths()
        height = self._get_secondary_height(index)
        left = self.screen_rect.x + widths[0] + self._get_main_width()
        top = self.screen_rect.y + self._get_relative_sizes_above(index)

        self._place_client(client, left, top, widths[1], height)

    def _get_main_width(self):
        """Calculate the main client's width"""
        return int(self.screen_rect.width * self.ratio)

    def _get_secondary_widths(self):
        """Calculate secondary clients' widths"""
        width = self.screen_rect.width - self._get_main_width()
        if len(self.clients) == 2:
            return [width, 0]

        return self._split_integer(width, 2)

    def _get_secondary_height(self, index):
        """Return the height of the provided index"""
        return self.relative_sizes[index - 1]

    def _get_relative_sizes_above(self, index):
        """Return the sum of the heights of all clients above the provided index"""
        column = self._get_column(index - 1)
        return sum(self.relative_sizes[column.start : index - 1])

    def _place_client(self, client, left, top, width, height):
        """Place a client on the screen

        Will prevent double margins by applying east and south margins only
        when the client is the rightmost or the bottommost window.
        """

        # Create a temporary margin list for the client
        if isinstance(self.margin, int):
            margin = [self.margin] * 4
        else:
            # We need to copy this list otherwise we'd be modifying self.margin!
            margin = self.margin.copy()

        rightmost = left + width - self.screen_rect.x + margin[1] >= self.screen_rect.width
        bottommost = top + height - self.screen_rect.y + margin[2] >= self.screen_rect.height

        if not rightmost:
            margin[1] = 0
        if not bottommost:
            margin[2] = 0

        client.place(
            left,
            top,
            width - 2 * self.border_width,
            height - 2 * self.border_width,
            self.border_width,
            self.border_focus if client.has_focus else self.border_normal,
            margin=margin,
        )

    @expose_command()
    def normalize(self, redraw=True):
        """Evenly distribute screen-space among secondary clients"""
        if self.screen_rect is not None:
            self.relative_sizes = []

            height = self.screen_rect.height
            left, right = self._get_columns()

            if left.count > 0:
                self.relative_sizes += self._split_integer(height, left.count)
            if right.count > 0:
                self.relative_sizes += self._split_integer(height, right.count)

        if redraw:
            self.group.layout_all()
        self.do_normalize = False

    @expose_command()
    def swap_main(self):
        """Swap current window to main pane"""
        self.swap(self.clients.current_client, self.clients[0])

    def _maximize_secondary(self):
        """Maximize the focused secondary pane"""
        focused = self.focused - 1
        column = self._get_column(focused)
        if column.count == 1:
            return

        max_height = self.screen_rect.height - ((column.count - 1) * self.min_secondary_size)
        for i in range(column.start, column.end):
            self.relative_sizes[i] = max_height if i == focused else self.min_secondary_size

    def _grow_secondary(self, amt):
        """Grow the focused client in the secondary pane"""
        self._resize_secondary(amt)

    def _shrink_secondary(self, amt):
        """Shrink the focused client in the secondary pane"""
        self._resize_secondary(-amt)

    def _resize_secondary(self, amt):
        """Resize the focused secondary client

        If amt is positive, the client will grow. Conversely, if it's negative,
        the client will shrink. All other clients in the same column will get
        grown/shrunk so to accommodate the new height.
        """
        focused = self.focused - 1
        column = self._get_column(focused)

        if column.count == 1:
            return

        # Resizing is accomplished by doing the following:
        # - calculate how much each client in the column must shrink/grow
        #   so that the focused window can grow/shrink.
        # - iterate over all clients in the column and change their height
        #   (grow or shrink) as long as they can still be resized (both main
        #   and secondary windows).
        min_height = self.min_secondary_size
        idx = column.start
        step = amt // (column.count - 1)
        visited = 0
        while amt != 0:
            if idx != focused:
                focused_new_height = self.relative_sizes[focused] + step
                new_height = self.relative_sizes[idx] - step
                if focused_new_height >= min_height and new_height >= min_height:
                    self.relative_sizes[focused] += step
                    self.relative_sizes[idx] -= step
                    amt -= step
                    visited += 1

            idx += 1
            if idx == column.end:
                if visited == 0:
                    break

                idx = column.start
                visited = 0

        self.group.layout_all()

    def _get_column(self, index):
        """Get the column containing the provided index"""
        left, right = self._get_columns()
        return left if index < left.count else right

    def _get_columns(self):
        """Get all columns"""
        clients = len(self.clients) - 1
        clients = (clients // 2 + clients % 2, clients // 2)
        return (
            MonadThreeCol.__column(
                name="left",
                count=clients[0],
                start=0,
                end=clients[0],
            ),
            MonadThreeCol.__column(
                name="right",
                count=clients[1],
                start=clients[0],
                end=clients[0] + clients[1],
            ),
        )

    def info(self) -> dict[str, Any]:
        left, right = self._get_columns()
        d = MonadTall.info(self)
        d.update(
            secondary=dict(
                left=d["clients"][1 : left.end + 1] if left.count > 0 else [],
                right=d["clients"][right.start + 1 :] if right.count > 0 else [],
            )
        )
        return d

    @staticmethod
    def _split_integer(value, parts):
        """Divide an integer into equal parts and distribute the remainder"""
        result = [value // parts] * parts
        for i in range(value % parts):
            result[i] += 1
        return result
