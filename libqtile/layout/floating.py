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
# Copyright (c) 2019 Guangwang Huang
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
    {"wmclass": "file_progress"},
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

    def __init__(self, float_rules=None, no_reposition_match=None, **config):
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

        Floating layout will try to center most of floating windows by
        default (until hints are properly implemented), but if you don't
        want this to happen for certain windows that are centered by mistake,
        you can use ``no_reposition_match`` option to specify them and layout
        will rely on windows to position themselves in correct location on
        the screen.
        """
        Layout.__init__(self, **config)
        self._clients = []
        self.focused = None
        self.group = None
        self.float_rules = float_rules or DEFAULT_FLOAT_RULES
        self.no_reposition_match = no_reposition_match
        self._floating_clients_only = True  # If only floating clients are interested
        self.add_defaults(Floating.defaults)

    def match(self, win):
        """Used to default float some windows"""
        if win.window.get_wm_type() in self.auto_float_types:
            return True
        for rule_dict in self.float_rules:
            if win.match(**rule_dict):
                return True
        return False

    def _interested_in_client(self, client):
        '''Test if a client is interested in.'''
        floating = client.floating
        if (self._floating_clients_only and floating) or \
           (not self._floating_clients_only and not floating):
            return True
        return False

    def find_clients(self, group):
        """Find all clients belonging to a given group"""
        clients = []
        for c in self._clients:
            if (group is None or c.group is group) and self._interested_in_client(c):
                clients.append(c)
        return clients

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
        clients = self.find_clients(group)

        if clients:
            return clients[0]

    def focus_next(self, win):
        clients = self.find_clients(win.group)
        if win not in clients or win.group is None:
            return

        idx = clients.index(win)
        if len(clients) > idx + 1:
            return clients[idx + 1]

    def focus_last(self, group=None):
        clients = self.find_clients(group)

        if clients:
            return clients[-1]

    def focus_previous(self, win):
        clients = self.find_clients(win.group)
        if win not in clients or win.group is None:
            return

        idx = clients.index(win)
        if idx > 0:
            return clients[idx - 1]

    def focus(self, client):
        if self._interested_in_client(client):
            self.focused = client

    def blur(self):
        self.focused = None

    def configure(self, client, screen):
        # 'sun-awt-X11-XWindowPeer' is a dropdown used in Java application,
        # don't reposition it anywhere, let Java app to control it
        cls = client.window.get_wm_class() or ''
        is_java_dropdown = 'sun-awt-X11-XWindowPeer' in cls
        if is_java_dropdown:
            return

        if client.has_focus:
            bc = client.group.qtile.color_pixel(self.border_focus)
        else:
            bc = client.group.qtile.color_pixel(self.border_normal)
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
            win = client.group.qtile.windows_map.get(transient_for)
            if win is not None:
                # if transient for a window, place in the center of the window
                center_x = win.x + win.width / 2
                center_y = win.y + win.height / 2
            else:
                center_x = screen.x + screen.width / 2
                center_y = screen.y + screen.height / 2
                above = True

            x = center_x - client.width / 2
            y = center_y - client.height / 2

            # don't go off the right...
            x = min(x, screen.x + screen.width)
            # or left...
            x = max(x, screen.x)
            # or bottom...
            y = min(y, screen.y + screen.height)
            # or top
            y = max(y, screen.y)

            if not (self.no_reposition_match and self.no_reposition_match.compare(client)):
                client.x = int(round(x))
                client.y = int(round(y))

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
        self._clients.append(client)
        if self._interested_in_client(client):
            self.focused = client

    def remove(self, client):
        if client not in self._clients:
            return

        next_focus = self.focus_next(client)
        if client is self.focused:
            self.blur()
        self._clients.remove(client)
        return next_focus

    def info(self):
        d = Layout.info(self)
        d["clients"] = [c.name for c in self.find_clients(group=None)]
        return d

    def cmd_next(self):
        # This can't ever be called, but implement the abstract method
        pass

    def cmd_previous(self):
        # This can't ever be called, but implement the abstract method
        pass


class FloatingTile(Floating):
    '''Floating layout for tile layouts config: the `layouts` symbol in config.py.

    It is almost exact with Floating, except that it's intended to be use a tile layout.'''

    defaults = [
        ("name", "floatingtile", "Name of this layout.")
    ]

    def __init__(self, **config):
        Floating.__init__(self, **config)
        self._floating_clients_only = False
        self.add_defaults(FloatingTile.defaults)
