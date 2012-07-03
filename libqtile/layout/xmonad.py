from base import SingleWindow
from .. import manager


class MonadTall(SingleWindow):
    """
    This layout attempts to emulate the behavior of XMonad's default
    tiling scheme.

    Main-Pane:

    A main pane that contains a single window takes up a vertical
    portion of the screen based on the ratio setting. This ratio can
    be adjusted with the `cmd_grow' and `cmd_shrink' methods while
    the main pane is in focus.

        ---------------------
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        |            |      |
        ---------------------

    Using the `cmd_flip' method will switch which horizontal side the
    main pane will occupy. The main pane is considered the "top" of
    the stack.

        ---------------------
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        |      |            |
        ---------------------

    Secondary-panes:

    Occupying the rest of the screen are one or more secondary panes.
    The secondary panes will share the vertical space of the screen
    however they can be resized at will with the `cmd_grow' and
    `cmd_shrink' methods. The other secondary panes will adjust their
    sizes to smoothly fill all of the space.

        ---------------------          ---------------------
        |            |      |          |            |______|
        |            |______|          |            |      |
        |            |      |          |            |      |
        |            |______|          |            |      |
        |            |      |          |            |______|
        |            |      |          |            |      |
        ---------------------          ---------------------

    Panes can be moved with the `cmd_shuffle_up' and `cmd_shuffle_down'
    methods. As mentioned the main pane is considered the top of the
    stack; moving up is counter-clockwise and moving down is clockwise.

    The opposite is true if the layout is "flipped".

        ---------------------          ---------------------
        |            |  2   |          |   2   |           |
        |            |______|          |_______|           |
        |            |  3   |          |   3   |           |
        |     1      |______|          |_______|     1     |
        |            |  4   |          |   4   |           |
        |            |      |          |       |           |
        ---------------------          ---------------------


    Normalizing:

    To restore all client windows to their default size ratios simply
    use the `cmd_normalize' method.


    Maximizing:

    To toggle a client window between its minimum and maximum sizes
    simply use the `cmd_maximize' on a focused client.

    Suggested Bindings:

    Key([modkey], "k", lazy.layout.down()),
    Key([modkey], "j", lazy.layout.up()),
    Key([modkey, "shift"], "k", lazy.layout.shuffle_down()),
    Key([modkey, "shift"], "j", lazy.layout.shuffle_up()),
    Key([modkey], "i", lazy.layout.grow()),
    Key([modkey], "m", lazy.layout.shrink()),
    Key([modkey], "n", lazy.layout.normalize()),
    Key([modkey], "o", lazy.layout.maximize()),
    Key([modkey, "shift"], "space", lazy.layout.flip()),

    """
    name = "xmonad-tall"
    _left = 0
    _right = 1
    _min_height = 85
    _min_ratio = .25
    _med_ratio = .5
    _max_ratio = .75

    defaults = manager.Defaults(
        ("border_focus", "#ff0000", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 2, "Border width."),
        ("name", "xmonad-tall", "Name of this layout."),
    )

    def __init__(self, ratio=_med_ratio, align=_left, change_ratio=.05,
                 change_size=20, **config):
        """
            - ratio       : The percent of the screen-space the
                            master pane should occupy by default.

            - align       : Which side the master pane will be placed.

            - change_size : Resize change in pixels
        """
        SingleWindow.__init__(self, **config)
        self.clients = []
        self.sizes = []
        self.ratio = ratio
        self.align = align
        self.change_size = change_size
        self.change_ratio = change_ratio
        self._focus = 0

    # track client that has 'focus'
    def _get_focus(self):
        return self._focus

    def _set_focus(self, x):
        if len(self.clients) > 0:
            self._focus = abs(x % len(self.clients))
        else:
            self._focus = 0
    focused = property(_get_focus, _set_focus)

    def _get_window(self):
        "Get currently focused client"
        if self.clients:
            return self.clients[self.focused]

    def focus(self, c):
        "Set focus to specified client"
        self.focused = self.clients.index(c)

    def clone(self, group):
        "Clone layout for other groups"
        c = SingleWindow.clone(self, group)
        c.clients = []
        c.sizes = []
        c.ratio = self.ratio
        c.align = self.align
        c._focus = 0
        return c

    def add(self, c):
        "Add client to layout"
        self.clients.insert(self.focused + 1, c)
        if self.group.screen:
            self.cmd_normalize()

    def remove(self, c):
        "Remove client from layout"
        # get index of removed client
        idx = self.clients.index(c)
        # remove the client
        self.clients.remove(c)
        # move focus pointer
        self.focused = max(0, idx - 1)
        # reposition all clients
        self.cmd_normalize()
        if self.clients:
            return self.clients[self.focused]

    def cmd_normalize(self, redraw=True):
        "Evenly distribute screen-space among secondary clients"
        n = len(self.clients) - 1  # exclude main client, 0
        if n > 0:  # if secondary clients exist
            self.sizes = []
            height = self.group.screen.dheight / n
            # set all sizes to calculated ratio
            for i in range(n):
                self.sizes.append(height)
        # reset main pane ratio
        if redraw:
            self.group.layoutAll()

    def _maximize_main(self):
        "Toggle the main pane between min and max size"
        if self.ratio <= self._med_ratio:
            self.ratio = self._max_ratio
        else:
            self.ratio = self._min_ratio
        self.group.layoutAll()

    def _maximize_secondary(self):
        "Toggle the focused secondary pane between min and max size"
        n = len(self.clients) - 2  # total shrinking clients
        # total height of collapsed secondaries
        collapsed_height = self._min_height * n
        nidx = self.focused - 1  # focused size index
        # total height of maximized secondary
        maxed_size = self.group.screen.dheight - collapsed_height
        # if maximized or nearly maximized
        if abs(self.sizes[nidx] - maxed_size) < self.change_size:
            # minimize
            self._shrink_secondary(self.sizes[nidx] - self._min_height)
        # otherwise maximize
        else:
            self._grow_secondary(maxed_size)

    def cmd_maximize(self):
        "Grow the currently focused client to the max size"
        # if we have 1 or 2 panes or main pane is focused
        if (len(self.clients) < 3 or self.focused == 0):
            self._maximize_main()
        # secondary is focused
        else:
            self._maximize_secondary()
        self.group.layoutAll()

    def configure(self, c, screen):
        "Position client based on order and sizes"
        # if no sizes, normalize
        if not self.sizes:
            self.cmd_normalize(False)
        # if client in this layout
        if self.clients and c in self.clients:
            # single client - fullscreen
            if len(self.clients) == 1:
                px = self.group.qtile.colorPixel(self.border_focus)
                c.place(self.group.screen.dx,
                        self.group.screen.dy,
                        self.group.screen.dwidth,
                        self.group.screen.dheight,
                        0, px)
                c.unhide()
                return
            # multiple clients
            else:
                # determine focus border-color
                if self.clients.index(c) == self.focused:
                    px = self.group.qtile.colorPixel(self.border_focus)
                else:
                    px = self.group.qtile.colorPixel(self.border_normal)

                # calculate main/secondary column widths
                width_main = int(self.group.screen.dwidth * self.ratio)
                width_shared = self.group.screen.dwidth - width_main

                # calculate client's x offset
                if self.align == self._left:  # left orientation
                    if self.clients.index(c) == 0:
                        # main client
                        xpos = self.group.screen.dx
                    else:
                        # secondary client
                        xpos = self.group.screen.dx + width_main
                else:  # right orientation
                    if self.clients.index(c) == 0:
                        # main client
                        xpos = self.group.screen.dx + width_shared
                    else:
                        # secondary client
                        xpos = self.group.screen.dx

                # calculate client width
                if self.clients.index(c) == 0:
                    # main client
                    width = width_main - 2 * self.border_width
                else:
                    # secondary client
                    width = width_shared - 2 * self.border_width

                # calculate client height and place
                cidx = self.clients.index(c)
                if cidx > 0:
                    # secondary client
                    # ypos is the sum of all clients above it
                    ypos = self.group.screen.dy + sum(self.sizes[:cidx - 1])
                    # get height from precalculated height list
                    height = self.sizes[cidx - 1]
                    # place client based on calculated dimensions
                    c.place(xpos, ypos,
                            width, height - 2 * self.border_width,
                            self.border_width, px)
                    c.unhide()
                else:
                    # main client
                    c.place(xpos, self.group.screen.dy, width,
                            self.group.screen.dheight - 2 * self.border_width,
                        self.border_width, px)
                    c.unhide()
        else:
            c.hide()

    def get_shrink_margin(self, cidx):
        "Return how many remaining pixels a client can shrink"
        return max(0, self.sizes[cidx] - self._min_height)

    def shrink(self, cidx, amt):
        """
        Reduce the size of a client. Will only shrink the client
        until it reaches the configured minimum size. Any amount
        that was prevented in the resize is returned.
        """
        # get max resizable amount
        margin = self.get_shrink_margin(cidx)
        if amt > margin:  # too much
            self.sizes[cidx] -= margin
            return amt - margin
        else:
            self.sizes[cidx] -= amt
            return 0

    def shrink_up(self, cidx, amt):
        """
        Will shrink all secondary clients above the specified
        index in order. Each client will attempt to shrink as
        much as it is able before the next client is resized.

        Any amount that was unable to be applied to the
        clients is returned.
        """
        left = amt  # track unused shrink amount
        # for each client before specified index
        for idx in range(0, cidx):
            # shrink by whatever is left-over of original amount
            left -= left - self.shrink(idx, left)
        # return unused shrink amount
        return left

    def shrink_up_shared(self, cidx, amt):
        """
        Will shrink all secondary clients above the specified
        index by an equal share of the provided amount. After
        applying the shared amount to all affected clients,
        any amount left over will be applied in a
        non-equal manner with `shrink_up'.

        Any amount that was unable to be applied to the
        clients is returned.
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
        """
        Will shrink all secondary clients below the specified
        index in order. Each client will attempt to shrink as
        much as it is able before the next client is resized.

        Any amount that was unable to be applied to the
        clients is returned.
        """
        left = amt  # track unused shrink amount
        # for each client after specified index
        for idx in range(cidx + 1, len(self.sizes)):
            # shrink by current total left-over amount
            left -= left - self.shrink(idx, left)
        # return unused shrink amount
        return left

    def shrink_down_shared(self, cidx, amt):
        """
        Will shrink all secondary clients below the specified
        index by an equal share of the provided amount. After
        applying the shared amount to all affected clients,
        any amount left over will be applied in a
        non-equal manner with `shrink_down'.

        Any amount that was unable to be applied to the
        clients is returned.
        """
        # split shrink amount among number of clients
        per_amt = amt / (len(self.sizes) - 1 - cidx)
        left = amt  # track unused shrink amount
        # for each client after specified index
        for idx in range(cidx + 1, len(self.sizes)):
            # shrink by equal amount and track left-over
            left -= per_amt - self.shrink(idx, per_amt)
        # apply non-equal shinkage secondary pass
        # in order to use up any left over shrink amounts
        left = self.shrink_down(cidx, left)
        # return whatever could not be applied
        return left

    def _grow_main(self, amt):
        """
        Will grow the client that is currently
        in the main pane.
        """
        self.ratio += amt
        self.ratio = min(self._max_ratio, self.ratio)

    def _grow_solo_secondary(self, amt):
        """
        Will grow the solitary client in the
        secondary pane.
        """
        self.ratio -= amt
        self.ratio = max(self._min_ratio, self.ratio)

    def _grow_secondary(self, amt):
        """
        Will grow the focused client in the
        secondary pane.
        """
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
            left -= amt - self.shrink_up(len(self.sizes) - 1, amt)
        # middle secondary
        else:
            # get size index
            idx = self.focused - 1
            # shrink up and down
            left -= half_change_size - self.shrink_up_shared(
                idx, half_change_size)
            left -= half_change_size - self.shrink_down_shared(
                idx, half_change_size)
            left -= half_change_size - self.shrink_up_shared(
                idx, half_change_size)
            left -= half_change_size - self.shrink_down_shared(
                idx, half_change_size)
        # calculate how much shrinkage took place
        diff = amt - left
        # grow client by diff amount
        self.sizes[self.focused - 1] += diff

    def cmd_grow(self):
        """
        Will grow the currently focused client reducing the
        size of those around it. Growing will stop when no
        other secondary clients can reduce their size any
        further.
        """
        # get currently focused client
        self.clients[self.focused]
        if self.focused == 0:
            self._grow_main(self.change_ratio)
        elif len(self.clients) == 2:
            self._grow_solo_secondary(self.change_ratio)
        else:
            self._grow_secondary(self.change_size)
        self.group.layoutAll()

    def grow(self, cidx, amt):
        "Grow secondary client by specified amount"
        self.sizes[cidx] += amt

    def grow_up_shared(self, cidx, amt):
        """
        Will grow all secondary clients above the specified
        index by an equal share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / cidx
        for idx in range(0, cidx):
            self.grow(idx, per_amt)

    def grow_down_shared(self, cidx, amt):
        """
        Will grow all secondary clients below the specified
        index by an equal share of the provided amount.
        """
        # split grow amount among number of clients
        per_amt = amt / (len(self.sizes) - 1 - cidx)
        for idx in range(cidx + 1, len(self.sizes)):
            self.grow(idx, per_amt)

    def _shrink_main(self, amt):
        """
        Will shrink the client that currently
        in the main pane.
        """
        self.ratio -= amt
        self.ratio = max(self._min_ratio, self.ratio)

    def _shrink_solo_secondary(self, amt):
        """
        Will shrink the solitary client in the
        secondary pane.
        """
        self.ratio += amt
        self.ratio = min(self._max_ratio, self.ratio)

    def _shrink_secondary(self, amt):
        """
        Will shrink the focused client in the
        secondary pane.
        """
        # get focused client
        c = self.clients[self.focused]

        # get default change size
        change = amt

        # get left-over height after change
        left = c.height - amt
        # if change would violate min_height
        if left < self._min_height:
            # just reduce to min_height
            change = c.height - self._min_height

        # calculate half of that change
        half_change = change / 2

        # first secondary (top)
        if self.focused == 1:
            # only grow downwards
            self.grow_down_shared(0, change)
        # last secondary (bottom)
        elif self.focused == len(self.clients) - 1:
            # only grow upwards
            self.grow_up_shared(len(self.sizes) - 1, change)
        # middle secondary
        else:
            idx = self.focused - 1
            # grow up and down
            self.grow_up_shared(idx, half_change)
            self.grow_down_shared(idx, half_change)
        # shrink client by total change
        self.sizes[self.focused - 1] -= change

    def cmd_shrink(self):
        """
        Will shrink the currently focused client reducing the
        size of those around it. Shrinking will stop when the
        client has reached the minimum size.
        """
        self.clients[self.focused]
        if self.focused == 0:
            self._shrink_main(self.change_ratio)
        elif len(self.clients) == 2:
            self._shrink_solo_secondary(self.change_ratio)
        else:
            self._shrink_secondary(self.change_size)
        self.group.layoutAll()

    def cmd_up(self):
        "Focus on the next more prominent client on the stack"
        self.focused -= 1
        self.group.focus(self.clients[self.focused], False)

    def cmd_down(self):
        "Focus on the less prominent client on the stack"
        self.focused += 1
        self.group.focus(self.clients[self.focused], False)

    def cmd_shuffle_up(self):
        "Shuffle the client up the stack."
        _oldf = self.focused
        self.focused -= 1
        self.clients[_oldf], self.clients[self.focused] = \
            self.clients[self.focused], self.clients[_oldf]
        self.group.layoutAll()
        self.group.focus(self.clients[self.focused], False)

    def cmd_shuffle_down(self):
        "Shuffle the client down the stack."
        _oldf = self.focused
        self.focused += 1
        self.clients[_oldf], self.clients[self.focused] = \
            self.clients[self.focused], self.clients[_oldf]
        self.group.layoutAll()
        self.group.focus(self.clients[self.focused], False)

    def cmd_flip(self):
        "Flip the layout horizontally."
        self.align = self._left if self.align == self._right else self._right
        self.group.layoutAll()
