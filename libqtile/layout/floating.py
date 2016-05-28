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

from .base import Layout

DEFAULT_FLOAT_WM_TYPES = set([
    'utility',
    'notification',
    'toolbar',
    'splash',
    'dialog',
])

DEFAULT_FLOAT_RULES = [
    {"role": "About"},
]


class Floating(Layout):
    """
    Floating layout, which does nothing with windows but handles focus order
    """
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("max_border_width", 0, "Border width for maximize."),
        ("fullscreen_border_width", 0, "Border width for fullscreen."),
        ("name", "floating", "Name of this layout."),
        (
            "auto_float_types",
            DEFAULT_FLOAT_WM_TYPES,
            "default wm types to automatically float"
        ),
    ]

    def __init__(self, float_rules=None, **config):
        """
        If you have certain apps that you always want to float you can provide
        ``float_rules`` to do so. ``float_rules`` is a list of
        dictionaries containing some or all of the keys::

            {'wname': WM_NAME, 'wmclass': WM_CLASS, 'role': WM_WINDOW_ROLE}

        The keys must be specified as above.  You only need one, but
        you need to provide the value for it.  When a new window is
        opened it's ``match`` method is called with each of these
        rules.  If one matches, the window will float.  The following
        will float gimp and skype::

            float_rules=[dict(wmclass="skype"), dict(wmclass="gimp")]

        Specify these in the ``floating_layout`` in your config.
        """
        Layout.__init__(self, **config)
        self.clients = []
        self.focused = None
        self.group = None
        self.float_rules = float_rules or DEFAULT_FLOAT_RULES
        self.add_defaults(Floating.defaults)

    def match(self, win):
        """Used to default float some windows"""
        if win.window.get_wm_type() in self.auto_float_types:
            return True
        for rule_dict in self.float_rules:
            if win.match(**rule_dict):
                return True
        return False

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
                # catch if the client hasn't been configured
                try:
                    # By default, place window at same offset from top corner
                    new_x = new_screen.x + win.float_x
                    new_y = new_screen.y + win.float_y
                except AttributeError:
                    # this will be handled in .configure()
                    pass
                else:
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

    def configure(self, client, screen):
        if client is self.focused:
            bc = client.group.qtile.colorPixel(self.border_focus)
        else:
            bc = client.group.qtile.colorPixel(self.border_normal)
        if client.maximized:
            bw = self.max_border_width
        elif client.fullscreen:
            bw = self.fullscreen_border_width
        else:
            bw = self.border_width
        above = False

        # We definitely have a screen here, so let's be sure we'll float on screen
        try:
            client.float_x
            client.float_y
        except AttributeError:
            # this window hasn't been placed before, let's put it in a sensible spot
            transient_for = client.window.get_wm_transient_for()
            win = client.group.qtile.windowMap.get(transient_for)
            if win is not None:
                x = win.x + (win.width - client.width) // 2
                y = win.y + (win.height - client.height) // 2
                above = True
            else:
                x = screen.x + client.x % screen.width
                # try to get right edge on screen (without moving the left edge off)
                x = min(x, screen.x - client.width)
                x = max(x, screen.x)
                # then update it's position (`.place()` will take care of `.float_x`)
                client.x = x

                y = screen.y + client.y % screen.height
                y = min(y, screen.y - client.height)
                y = max(y, screen.y)
                client.y = y

        client.place(
            client.x,
            client.y,
            client.width,
            client.height,
            bw,
            bc,
            above,
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
