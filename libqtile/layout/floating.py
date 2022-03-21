# Copyright (c) 2010 matt
# Copyright (c) 2010-2011 Paul Colomiets
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Julien Iguchi-Cartigny
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dequis
# Copyright (c) 2018 Nazar Mokrynskyi
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

from libqtile.backend.base import Window
from libqtile.config import Match
from libqtile.layout.base import Layout


class Floating(Layout):
    """
    Floating layout, which does nothing with windows but handles focus order
    """

    default_float_rules = [
        Match(wm_type="utility"),
        Match(wm_type="notification"),
        Match(wm_type="toolbar"),
        Match(wm_type="splash"),
        Match(wm_type="dialog"),
        Match(wm_class="file_progress"),
        Match(wm_class="confirm"),
        Match(wm_class="dialog"),
        Match(wm_class="download"),
        Match(wm_class="error"),
        Match(wm_class="notification"),
        Match(wm_class="splash"),
        Match(wm_class="toolbar"),
        Match(func=lambda c: c.has_fixed_size()),
        Match(func=lambda c: c.has_fixed_ratio()),
    ]

    defaults = [
        ("border_focus", "#0000ff", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("max_border_width", 0, "Border width for maximize."),
        ("fullscreen_border_width", 0, "Border width for fullscreen."),
    ]

    def __init__(
        self, float_rules: list[Match] | None = None, no_reposition_rules=None, **config
    ):
        """
        If you have certain apps that you always want to float you can provide
        ``float_rules`` to do so. ``float_rules`` are a list of
        Match objects::

            from libqtile.config import Match
            Match(title=WM_NAME, wm_class=WM_CLASS, role=WM_WINDOW_ROLE)

        When a new window is opened its ``match`` method is called with each of
        these rules.  If one matches, the window will float.  The following
        will float GIMP and Skype::

            from libqtile.config import Match
            float_rules=[Match(wm_class="skype"), Match(wm_class="gimp")]

        The following ``Match`` will float all windows that are transient windows for a
        parent window:

            Match(func=lambda c: bool(c.is_transient_for()))

        Specify these in the ``floating_layout`` in your config.

        Floating layout will try to center most of floating windows by default,
        but if you don't want this to happen for certain windows that are
        centered by mistake, you can use ``no_reposition_rules`` option to
        specify them and layout will rely on windows to position themselves in
        correct location on the screen.
        """
        Layout.__init__(self, **config)
        self.clients: list[Window] = []
        self.focused = None
        self.group = None

        if float_rules is None:
            float_rules = self.default_float_rules

        self.float_rules = float_rules
        self.no_reposition_rules = no_reposition_rules or []
        self.add_defaults(Floating.defaults)

    def match(self, win):
        """Used to default float some windows"""
        return any(win.match(rule) for rule in self.float_rules)

    def find_clients(self, group):
        """Find all clients belonging to a given group"""
        return [c for c in self.clients if c.group is group]

    def to_screen(self, group, new_screen):
        """Adjust offsets of clients within current screen"""
        for win in self.find_clients(group):
            if win.maximized:
                win.maximized = True
            elif win.fullscreen:
                win.fullscreen = True
            else:
                # If the window hasn't been floated before, it will be configured in
                # .configure()
                if win.float_x is not None and win.float_y is not None:
                    # By default, place window at same offset from top corner
                    new_x = new_screen.x + win.float_x
                    new_y = new_screen.y + win.float_y
                    # make sure window isn't off screen left/right...
                    new_x = min(new_x, new_screen.x + new_screen.width - win.width)
                    new_x = max(new_x, new_screen.x)
                    # and up/down
                    new_y = min(new_y, new_screen.y + new_screen.height - win.height)
                    new_y = max(new_y, new_screen.y)

                    win.x = new_x
                    win.y = new_y
            win.group = new_screen.group

    def focus_first(self, group=None):
        if group is None:
            clients = self.clients
        else:
            clients = self.find_clients(group)

        if clients:
            return clients[0]

    def focus_next(self, win):
        if win not in self.clients or win.group is None:
            return

        clients = self.find_clients(win.group)
        idx = clients.index(win)
        if len(clients) > idx + 1:
            return clients[idx + 1]

    def focus_last(self, group=None):
        if group is None:
            clients = self.clients
        else:
            clients = self.find_clients(group)

        if clients:
            return clients[-1]

    def focus_previous(self, win):
        if win not in self.clients or win.group is None:
            return

        clients = self.find_clients(win.group)
        idx = clients.index(win)
        if idx > 0:
            return clients[idx - 1]

    def focus(self, client):
        self.focused = client

    def blur(self):
        self.focused = None

    def on_screen(self, client, screen_rect):
        if client.x < screen_rect.x:  # client's left edge
            return False
        if screen_rect.x + screen_rect.width < client.x + client.width:  # right
            return False
        if client.y < screen_rect.y:  # top
            return False
        if screen_rect.y + screen_rect.width < client.y + client.height:  # bottom
            return False
        return True

    def compute_client_position(self, client, screen_rect):
        """recompute client.x and client.y, returning whether or not to place
        this client above other windows or not"""
        above = True

        if client.has_user_set_position() and not self.on_screen(client, screen_rect):
            # move to screen
            client.x = screen_rect.x + client.x
            client.y = screen_rect.y + client.y
        if not client.has_user_set_position() or not self.on_screen(client, screen_rect):
            # client has not been properly placed before or it is off screen
            transient_for = client.is_transient_for()
            if transient_for is not None:
                # if transient for a window, place in the center of the window
                center_x = transient_for.x + transient_for.width / 2
                center_y = transient_for.y + transient_for.height / 2
                above = False
            else:
                center_x = screen_rect.x + screen_rect.width / 2
                center_y = screen_rect.y + screen_rect.height / 2

            x = center_x - client.width / 2
            y = center_y - client.height / 2

            # don't go off the right...
            x = min(x, screen_rect.x + screen_rect.width - client.width)
            # or left...
            x = max(x, screen_rect.x)
            # or bottom...
            y = min(y, screen_rect.y + screen_rect.height - client.height)
            # or top
            y = max(y, screen_rect.y)

            client.x = int(round(x))
            client.y = int(round(y))
        return above

    def configure(self, client, screen_rect):
        if client.has_focus:
            bc = self.border_focus
        else:
            bc = self.border_normal

        if client.maximized:
            bw = self.max_border_width
        elif client.fullscreen:
            bw = self.fullscreen_border_width
        else:
            bw = self.border_width

        # 'sun-awt-X11-XWindowPeer' is a dropdown used in Java application,
        # don't reposition it anywhere, let Java app to control it
        cls = client.get_wm_class() or ""
        is_java_dropdown = "sun-awt-X11-XWindowPeer" in cls
        if is_java_dropdown:
            client.paint_borders(bc, bw)
            client.cmd_bring_to_front()

        # alternatively, users may have asked us explicitly to leave the client alone
        elif any(m.compare(client) for m in self.no_reposition_rules):
            client.paint_borders(bc, bw)
            client.cmd_bring_to_front()

        else:
            above = False

            # We definitely have a screen here, so let's be sure we'll float on screen
            if client.float_x is None or client.float_y is None:
                # this window hasn't been placed before, let's put it in a sensible spot
                above = self.compute_client_position(client, screen_rect)

            client.place(
                client.x,
                client.y,
                client.width,
                client.height,
                bw,
                bc,
                above,
                respect_hints=True,
            )
        client.unhide()

    def add(self, client):
        self.clients.append(client)
        self.focused = client

    def remove(self, client):
        if client not in self.clients:
            return

        next_focus = self.focus_next(client)
        if client is self.focused:
            self.blur()
        self.clients.remove(client)
        return next_focus

    def get_windows(self):
        return self.clients

    def info(self):
        d = Layout.info(self)
        d["clients"] = [c.name for c in self.clients]
        return d

    def cmd_next(self):
        # This can't ever be called, but implement the abstract method
        pass

    def cmd_previous(self):
        # This can't ever be called, but implement the abstract method
        pass
