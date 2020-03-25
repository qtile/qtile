# -*- coding: utf-8 -*-
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

from .base import _SimpleLayoutBase
import math


class MonadTall(_SimpleLayoutBase):
    """Emulate the behavior of XMonad's default tiling scheme.

    Main-Pane:

    A main pane that contains a single window takes up a vertical portion of
    the screen based on the ratio setting. This ratio can be adjusted with the
    ``cmd_grow_main`` and ``cmd_shrink_main`` or, while the main pane is in
    focus, ``cmd_grow`` and ``cmd_shrink``.

    ::

        ---------------------
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        ---------------------

    Using the ``cmd_flip`` method will switch which horizontal side the main
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

    Occupying the rest of the screen are one or more secondary panes.  The
    secondary panes will share the vertical space of the screen however they
    can be resized at will with the ``cmd_grow`` and ``cmd_shrink`` methods.
    The other secondary panes will adjust their sizes to smoothly fill all of
    the space.

    ::

        ---------------------          ---------------------
        |            |      |          |            |______|
        |            |______|          |            |      |
        |            |      |          |            |      |
        |            |______|          |            |      |
        |            |      |          |            |______|
        |            |      |          |            |      |
        ---------------------          ---------------------

    Panes can be moved with the ``cmd_shuffle_up`` and ``cmd_shuffle_down``
    methods. As mentioned the main pane is considered the top of the stack;
    moving up is counter-clockwise and moving down is clockwise.

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


    Normalizing:

    To restore all client windows to their default size ratios simply use the
    ``cmd_normalize`` method.

    Maximizing:

    To toggle a client window between its minimum and maximum sizes
    simply use the ``cmd_maximize`` on a focused client.

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
        Key([modkey], "n", lazy.layout.normalize()),
        Key([modkey], "o", lazy.layout.maximize()),
        Key([modkey, "shift"], "space", lazy.layout.flip()),
    """

    _left = 0
    _right = 1
    _med_ratio = 0.5

    defaults = [
        ("border_focus", "#ff0000", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_width", 2, "Border width."),
        ("single_border_width", None, "Border width for single window"),
        ("single_margin", None, "Margin size for single window"),
        ("name", "xmonadtall", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
        ("ratio", .5,
            "The percent of the screen-space the master pane should occupy "
            "by default."),
        ("min_ratio", .25,
            "The percent of the screen-space the master pane should occupy "
            "at minimum."),
        ("max_ratio", .75,
            "The percent of the screen-space the master pane should occupy "
            "at maximum."),
        ("min_secondary_size", 85,
            "minimum size in pixel for a secondary pane window "),
        ("align", _left, "Which side master plane will be placed "
            "(one of ``MonadTall._left`` or ``MonadTall._right``)"),
        ("change_ratio", .05, "Resize ratio"),
        ("change_size", 20, "Resize change in pixels"),
        ("new_at_current", False,
            "Place new windows at the position of the active window."),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(MonadTall.defaults)
        if self.single_border_width is None:
            self.single_border_width = self.border_width
        if self.single_margin is None:
            self.single_margin = self.margin
        self.relative_sizes = []

    @property
    def focused(self):
        return self.clients.current_index

    def _get_relative_size_from_absolute(self, absolute_size):
        return absolute_size / self.group.screen.dheight

    def _get_absolute_size_from_relative(self, relative_size):
        return int(relative_size * self.group.screen.dheight)

    def clone(self, group):
        "Clone layout for other groups"
        c = _SimpleLayoutBase.clone(self, group)
        c.sizes = []
        c.relative_sizes = []
        c.ratio = self.ratio
        c.align = self.align
        return c

    def add(self, client):
        "Add client to layout"
        self.clients.add(client, 0 if self.new_at_current else 1)
        self.do_normalize = True

    def remove(self, client):
        "Remove client from layout"
        self.do_normalize = True
        return self.clients.remove(client)

    def cmd_normalize(self, redraw=True):
        "Evenly distribute screen-space among secondary clients"
        n = len(self.clients) - 1  # exclude main client, 0
        # if secondary clients exist
        if n > 0 and self.group.screen is not None:
            self.relative_sizes = [1.0 / n] * n
        # reset main pane ratio
        if redraw:
            self.group.layout_all()
        self.do_normalize = False

    def cmd_reset(self, redraw=True):
        "Reset Layout."
        self.ratio = self._med_ratio
        if self.align == self._right:
            self.align = self._left
        self.cmd_normalize(redraw)

    def _maximize_main(self):
        "Toggle the main pane between min and max size"
        if self.ratio <= self._med_ratio:
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
        if abs(
            self._get_absolute_size_from_relative(self.relative_sizes[nidx]) -
            maxed_size
        ) < self.change_size:
            # minimize
            self._shrink_secondary(
                self._get_absolute_size_from_relative(
                    self.relative_sizes[nidx]
                ) - self.min_secondary_size
            )
        # otherwise maximize
        else:
            self._grow_secondary(maxed_size)

    def cmd_maximize(self):
        "Grow the currently focused client to the max size"
        # if we have 1 or 2 panes or main pane is focused
        if len(self.clients) < 3 or self.focused == 0:
            self._maximize_main()
        # secondary is focused
        else:
            self._maximize_secondary()
        self.group.layout_all()

    def configure(self, client, screen):
        "Position client based on order and sizes"
        # if no sizes or normalize flag is set, normalize
        if not self.relative_sizes or self.do_normalize:
            self.cmd_normalize(False)

        # if client not in this layout
        if not self.clients or client not in self.clients:
            client.hide()
            return

        # determine focus border-color
        if client.has_focus:
            px = self.group.qtile.color_pixel(self.border_focus)
        else:
            px = self.group.qtile.color_pixel(self.border_normal)

        # single client - fullscreen
        if len(self.clients) == 1:
            client.place(
                self.group.screen.dx,
                self.group.screen.dy,
                self.group.screen.dwidth - 2 * self.single_border_width,
                self.group.screen.dheight - 2 * self.single_border_width,
                self.single_border_width,
                px,
                margin=self.single_margin,
            )
            client.unhide()
            return
        cidx = self.clients.index(client)
        self._configure_specific(client, screen, px, cidx)
        client.unhide()

    def _configure_specific(self, client, screen, px, cidx):
        """Specific configuration for xmonad tall."""
        # calculate main/secondary pane size
        width_main = int(self.group.screen.dwidth * self.ratio)
        width_shared = self.group.screen.dwidth - width_main

        # calculate client's x offset
        if self.align == self._left:  # left or up orientation
            if cidx == 0:
                # main client
                xpos = self.group.screen.dx
            else:
                # secondary client
                xpos = self.group.screen.dx + width_main
        else:  # right or down orientation
            if cidx == 0:
                # main client
                xpos = self.group.screen.dx + width_shared - self.margin
            else:
                # secondary client
                xpos = self.group.screen.dx

        # calculate client height and place
        if cidx > 0:
            # secondary client
            width = width_shared - 2 * self.border_width
            # ypos is the sum of all clients above it
            ypos = self.group.screen.dy + \
                self._get_absolute_size_from_relative(
                    sum(self.relative_sizes[:cidx - 1])
                )
            # get height from precalculated height list
            height = self._get_absolute_size_from_relative(
                self.relative_sizes[cidx - 1]
            )
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
            width = width_main - 2 * self.border_width
            client.place(
                xpos + self.margin,
                self.group.screen.dy + self.margin,
                width - self.margin,
                (self.group.screen.dheight -
                    2 * self.border_width - 2 * self.margin),
                self.border_width,
                px,
            )

    def info(self):
        d = _SimpleLayoutBase.info(self)
        d.update(dict(
            main=d['clients'][0] if self.clients else None,
            secondary=d['clients'][1::] if self.clients else []))
        return d

    def get_shrink_margin(self, cidx):
        "Return how many remaining pixels a client can shrink"
        return max(
            0,
            self._get_absolute_size_from_relative(
                self.relative_sizes[cidx]
            ) - self.min_secondary_size
        )

    def shrink(self, cidx, amt):
        """Reduce the size of a client

        Will only shrink the client until it reaches the configured minimum
        size. Any amount that was prevented in the resize is returned.
        """
        # get max resizable amount
        margin = self.get_shrink_margin(cidx)
        if amt > margin:  # too much
            self.relative_sizes[cidx] -= \
                self._get_relative_size_from_absolute(margin)
            return amt - margin
        else:
            self.relative_sizes[cidx] -= \
                self._get_relative_size_from_absolute(amt)
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
        for idx in range(0, cidx):
            # shrink by whatever is left-over of original amount
            left -= left - self.shrink(idx, left)
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
        for idx in range(0, cidx):
            # shrink by equal amount and track left-over
            left -= per_amt - self.shrink(idx, per_amt)
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
            left -= left - self.shrink(idx, left)
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
            left -= per_amt - self.shrink(idx, per_amt)
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
            left -= half_change_size - self.shrink_up_shared(
                idx,
                half_change_size
            )
            left -= half_change_size - self.shrink_down_shared(
                idx,
                half_change_size
            )
            left -= half_change_size - self.shrink_up_shared(
                idx,
                half_change_size
            )
            left -= half_change_size - self.shrink_down_shared(
                idx,
                half_change_size
            )
        # calculate how much shrinkage took place
        diff = amt - left
        # grow client by diff amount
        self.relative_sizes[self.focused - 1] += \
            self._get_relative_size_from_absolute(diff)

    def cmd_grow(self):
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

    def cmd_grow_main(self):
        """Grow main pane

        Will grow the main pane, reducing the size of clients in the secondary
        pane.
        """
        self._grow_main(self.change_ratio)
        self.group.layout_all()

    def cmd_shrink_main(self):
        """Shrink main pane

        Will shrink the main pane, increasing the size of clients in the
        secondary pane.
        """
        self._shrink_main(self.change_ratio)
        self.group.layout_all()

    def grow(self, cidx, amt):
        "Grow secondary client by specified amount"
        self.relative_sizes[cidx] += self._get_relative_size_from_absolute(amt)

    def grow_up_shared(self, cidx, amt):
        """Grow higher secondary clients

        Will grow all secondary clients above the specified index by an equal
        share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / cidx
        for idx in range(0, cidx):
            self.grow(idx, per_amt)

    def grow_down_shared(self, cidx, amt):
        """Grow lower secondary clients

        Will grow all secondary clients below the specified index by an equal
        share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / (len(self.relative_sizes) - 1 - cidx)
        for idx in range(cidx + 1, len(self.relative_sizes)):
            self.grow(idx, per_amt)

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
        self.relative_sizes[self.focused - 1] -= \
            self._get_relative_size_from_absolute(change)

    cmd_next = _SimpleLayoutBase.next
    cmd_previous = _SimpleLayoutBase.previous

    def cmd_shrink(self):
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

    cmd_up = cmd_previous
    cmd_down = cmd_next

    def cmd_shuffle_up(self):
        """Shuffle the client up the stack"""
        self.clients.shuffle_up()
        self.group.layout_all()
        self.group.focus(self.clients.current_client)

    def cmd_shuffle_down(self):
        """Shuffle the client down the stack"""
        self.clients.shuffle_down()
        self.group.layout_all()
        self.group.focus(self.clients[self.focused])

    def cmd_flip(self):
        """Flip the layout horizontally"""
        self.align = self._left if self.align == self._right else self._right
        self.group.layout_all()

    def _get_closest(self, x, y, clients):
        """Get closest window to a point x,y"""
        target = min(
            clients,
            key=lambda c: math.hypot(c.info()['x'] - x, c.info()['y'] - y)
        )
        return target

    def cmd_swap(self, window1, window2):
        """Swap two windows"""
        self.clients.swap(window1, window2, 1)
        self.group.layout_all()
        self.group.focus(window1)

    def cmd_swap_left(self):
        """Swap current window with closest window to the left"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()['x'] < x]
        target = self._get_closest(x, y, candidates)
        self.cmd_swap(win, target)

    def cmd_swap_right(self):
        """Swap current window with closest window to the right"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()['x'] > x]
        target = self._get_closest(x, y, candidates)
        self.cmd_swap(win, target)

    def cmd_swap_main(self):
        """Swap current window to main pane"""
        if self.align == self._left:
            self.cmd_swap_left()
        elif self.align == self._right:
            self.cmd_swap_right()

    def cmd_left(self):
        """Focus on the closest window to the left of the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()['x'] < x]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)

    def cmd_right(self):
        """Focus on the closest window to the right of the current window"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()['x'] > x]
        self.clients.current_client = self._get_closest(x, y, candidates)
        self.group.focus(self.clients.current_client)

    cmd_shuffle_left = cmd_swap_left
    cmd_shuffle_right = cmd_swap_right


class MonadWide(MonadTall):
    """Emulate the behavior of XMonad's horizontal tiling scheme.

    This layout attempts to emulate the behavior of XMonad wide
    tiling scheme.

    Main-Pane:

    A main pane that contains a single window takes up a horizontal
    portion of the screen based on the ratio setting. This ratio can be
    adjusted with the ``cmd_grow_main`` and ``cmd_shrink_main`` or,
    while the main pane is in focus, ``cmd_grow`` and ``cmd_shrink``.

    ::

        ---------------------
        |                   |
        |                   |
        |                   |
        |___________________|
        |                   |
        |                   |
        ---------------------

    Using the ``cmd_flip`` method will switch which vertical side the
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

    Occupying the rest of the screen are one or more secondary panes.
    The secondary panes will share the horizontal space of the screen
    however they can be resized at will with the ``cmd_grow`` and
    ``cmd_shrink`` methods. The other secondary panes will adjust their
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

    Panes can be moved with the ``cmd_shuffle_up`` and ``cmd_shuffle_down``
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

    Normalizing:

    To restore all client windows to their default size ratios simply
    use the ``cmd_normalize`` method.


    Maximizing:

    To toggle a client window between its minimum and maximum sizes
    simply use the ``cmd_maximize`` on a focused client.

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
        Key([modkey], "n", lazy.layout.normalize()),
        Key([modkey], "o", lazy.layout.maximize()),
        Key([modkey, "shift"], "space", lazy.layout.flip()),
    """

    _up = 0
    _down = 1

    def _get_relative_size_from_absolute(self, absolute_size):
        return absolute_size / self.group.screen.dwidth

    def _get_absolute_size_from_relative(self, relative_size):
        return int(relative_size * self.group.screen.dwidth)

    def _maximize_secondary(self):
        """Toggle the focused secondary pane between min and max size."""
        n = len(self.clients) - 2  # total shrinking clients
        # total size of collapsed secondaries
        collapsed_size = self.min_secondary_size * n
        nidx = self.focused - 1  # focused size index
        # total width of maximized secondary
        maxed_size = self.group.screen.dwidth - collapsed_size
        # if maximized or nearly maximized
        if abs(
            self._get_absolute_size_from_relative(self.relative_sizes[nidx]) -
            maxed_size
        ) < self.change_size:
            # minimize
            self._shrink_secondary(
                self._get_absolute_size_from_relative(
                    self.relative_sizes[nidx]
                ) - self.min_secondary_size
            )
        # otherwise maximize
        else:
            self._grow_secondary(maxed_size)

    def _configure_specific(self, client, screen, px, cidx):
        """Specific configuration for xmonad wide."""
        # calculate main/secondary column widths
        height_main = int(self.group.screen.dheight * self.ratio)
        height_shared = self.group.screen.dheight - height_main

        # calculate client's x offset
        if self.align == self._up:  # up orientation
            if cidx == 0:
                # main client
                ypos = self.group.screen.dy
            else:
                # secondary client
                ypos = self.group.screen.dy + height_main
        else:  # right or down orientation
            if cidx == 0:
                # main client
                ypos = self.group.screen.dy + height_shared - self.margin
            else:
                # secondary client
                ypos = self.group.screen.dy

        # calculate client height and place
        if cidx > 0:
            # secondary client
            height = height_shared - 2 * self.border_width
            # xpos is the sum of all clients left of it
            xpos = self.group.screen.dx + \
                self._get_absolute_size_from_relative(
                    sum(self.relative_sizes[:cidx - 1])
                )
            # get width from precalculated witdh list
            width = self._get_absolute_size_from_relative(
                self.relative_sizes[cidx - 1]
            )
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
            height = height_main - 2 * self.border_width
            client.place(
                self.group.screen.dx + self.margin,
                ypos + self.margin,
                (self.group.screen.dwidth -
                    2 * self.border_width - 2 * self.margin),
                height - self.margin,
                self.border_width,
                px,
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
        self.relative_sizes[self.focused - 1] -= \
            self._get_relative_size_from_absolute(change)

    def cmd_swap_left(self):
        """Swap current window with closest window to the down"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients.clients if c.info()['y'] > y]
        target = self._get_closest(x, y, candidates)
        self.cmd_swap(win, target)

    def cmd_swap_right(self):
        """Swap current window with closest window to the up"""
        win = self.clients.current_client
        x, y = win.x, win.y
        candidates = [c for c in self.clients if c.info()['y'] < y]
        target = self._get_closest(x, y, candidates)
        self.cmd_swap(win, target)

    def cmd_swap_main(self):
        """Swap current window to main pane"""
        if self.align == self._up:
            self.cmd_swap_right()
        elif self.align == self._down:
            self.cmd_swap_left()
