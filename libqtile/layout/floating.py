from base import Layout
from .. import manager, window

DEFAULT_FLOAT_WM_TYPES = set([
    'utility',
    'notification',
    'toolbar',
    'splash',
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
        ("auto_float_types", DEFAULT_FLOAT_WM_TYPES,
            "default wm types to automatically float"),
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
        self.clients = []
        self.focused = None
        self.float_rules = float_rules or []
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

    def focus_next(self, win):
        idx = self.clients.index(win)
        if len(self.clients) > idx + 1:
            return self.clients[idx + 1]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_prev(self, win):
        idx = self.clients.index(win)
        if idx > 0:
            return self.clients[idx - 1]

    def focus(self, c):
        self.focused = c

    def blur(self):
        self.focused = None

    def configure(self, c, screen):
        if c is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        if c.maximized:
            bw = self.max_border_width
        elif c.fullscreen:
            bw = self.fullscreen_border_width
        else:
            bw = self.border_width
        c.place(c.x,
                c.y,
                c.width,
                c.height,
                bw,
                bc)
        c.unhide()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, c):
        self.clients.append(c)

    def remove(self, c):
        res = self.focus_next(c)
        self.clients.remove(c)
        return res

    def info(self):
        d = Layout.info(self)
        d["clients"] = [i.name for i in self.clients]
        return d
