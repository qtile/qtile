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
        ("border_normal", "#000000", "Border colour for un-focused winows."),
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
        self.float_rules = float_rules or DEFAULT_FLOAT_RULES
        self.add_defaults(Floating.defaults)

    def match(self, win):
        """
        Used to default float some windows.
        """
        if win.window.get_wm_type() in self.auto_float_types:
            return True
        for rule_dict in self.float_rules:
            if win.match(**rule_dict):
                return True
        return False

    def to_screen(self, new_screen):
        """
        Adjust offsets of clients within current screen
        """
        for i, win in enumerate(self.clients):
            if win.maximized:
                win.maximized = True
            elif win.fullscreen:
                win.fullscreen = True
            else:
                offset_x = win._float_info['x']
                offset_y = win._float_info['y']

                new_x = new_screen.x + offset_x
                new_y = new_screen.y + offset_y

                right_edge = new_screen.x + new_screen.width
                bottom_edge = new_screen.y + new_screen.height
                while new_x > right_edge:
                    new_x = (new_x - new_screen.x) // 2
                while new_y > bottom_edge:
                    new_y = (new_y - new_screen.y) // 2

                win.x = new_x
                win.y = new_y
            win.group = new_screen.group

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_next(self, win):
        if win not in self.clients:
            return
        idx = self.clients.index(win)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_previous(self, win):
        if win not in self.clients:
            return
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx - 1]

    def focus(self, client):
        self.focused = client

    def blur(self):
        self.focused = None

    def configure(self, client, screen):
        if client is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        if client.maximized:
            bw = self.max_border_width
        elif client.fullscreen:
            bw = self.fullscreen_border_width
        else:
            bw = self.border_width
        client.place(
            client.x,
            client.y,
            client.width,
            client.height,
            bw,
            bc
        )
        client.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        self.clients.append(client)
        self.focused = client

    def remove(self, client):
        if client not in self.clients:
            return
        self.focused = self.focus_next(client)
        self.clients.remove(client)
        return self.focused

    def info(self):
        d = Layout.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def cmd_next(self):
        client = self.focus_next(self.focused) or \
            self.focus_first()
        self.group.focus(client)

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or \
            self.focus_last()
        self.group.focus(client)
