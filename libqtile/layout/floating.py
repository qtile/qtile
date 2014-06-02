from base import Layout
from .. import window
from time import time

DEFAULT_FLOAT_WM_TYPES = set([
    'utility',
    'notification',
    'toolbar',
    'splash',
    'dialog',
])


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
        ("sloppyfocus", 5, "After many seconds to allow float windows to hide"),
    ]

    def __init__(self, float_rules=None, **config):
        """
        If you have certain apps that you always want to float you can
        provide ``float_rules`` to do so.
        ``float_rules`` is a list of dictionaries containing:

        {wname: WM_NAME, wmclass: WM_CLASS
        role: WM_WINDOW_ROLE}

        The keys must be specified as above.  You only need one, but
        you need to provide the value for it.  When a new window is
        opened it's ``match`` method is called with each of these
        rules.  If one matches, the window will float.  The following
        will float gimp and skype:

        float_rules=[dict(wmclass="skype"), dict(wmclass="gimp")]

        Specify these in the ``floating_layout`` in your config.
        """
        Layout.__init__(self, **config)
        self.add_defaults(Floating.defaults)
        self.float_rules = float_rules or []

        self.clients = []
        self.raised = []
        self.focused = None
        self.time = None

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
                win.enablemaximize()
                continue
            elif win.fullscreen:
                win.enablemaximize(state=window.FULLSCREEN)
                continue

            offset_x = win._float_info['x']
            offset_y = win._float_info['y']

            if offset_x > 0:
                new_x = new_screen.x + offset_x
            else:
                new_x = new_screen.x + i * 10
            if offset_y > 0:
                new_y = new_screen.y + offset_y
            else:
                new_y = new_screen.y + i * 10

            right_edge = new_screen.x + new_screen.width
            bottom_edge = new_screen.y + new_screen.height
            while new_x > right_edge:
                new_x = (new_x - new_screen.x) / 2
            while new_y > bottom_edge:
                new_y = (new_y - new_screen.y) / 2
            win.x = new_x
            win.y = new_y
            win.group = new_screen.group

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_next(self, client):
        try:
            index = self.clients.index(client)
        except ValueError:
            return
        try:
            return self.clients[index + 1]
        except IndexError:
            return

    def focus_previous(self, win):
        try:
            index = self.clients.index(client)
        except ValueError:
            return
        if index:
            return self.clients[index - 1]

    def focus(self, client):
        self.focused = client

    def blur(self):
        if not self.group.currentWindow in \
        self.raised:
            if self.sloppyfocus and \
            self.time and time() - self.time > self.sloppyfocus:
                self.time = None
                self.focused = None
                self.raised = []
            elif self.sloppyfocus and not self.time:
                self.time = time()

    def float_blur(self):
        self.focused = None
        self.raised = []

    def raisedecider(self, client):
        wm_transient_for = client.window.get_wm_transient_for()
        wm_client_leader = client.window.get_wm_client_leader()
        current_focused_wid = self.group.currentWindow.window.wid
        current_focused = self.group.currentWindow

        if current_focused_wid == (wm_transient_for or wm_client_leader) or \
            current_focused.window.get_wm_transient_for() == \
            wm_transient_for or \
            current_focused.window.get_wm_client_leader() == \
            wm_client_leader:
                if self.focused:
                    if client not in self.raised:
                        self.raised.append(client)
                    return True
                elif client in self.raised:
                    return True

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
            bc,
            self.raisedecider(client)
        )
        if self.raisedecider(client):
            client.unhide()
        else:
            client.hide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        self.clients.append(client)
        self.focused = client

    def remove(self, client):
        self.focused = self.focus_next(client)
        try:
            self.clients.remove(client)
        except ValueError:
            return
        return self.focused

    def info(self):
        d = Layout.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def cmd_next(self):
        client = self.focus_next(self.focused) or \
                 self.focus_first()
        self.group.focus(client, False)

    def cmd_previous(self):
        client = self.focus_previous(self.focused) or \
                 self.focus_last()
        self.group.focus(client, False)
