from .. import bar, hook, utils, manager
import base

class _GroupBase(base._Widget):
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    @property
    def fontsize(self):
        if self._fontsize is None:
            return self.bar.height - self.margin_y*2 - self.borderwidth*2 - self.padding*2
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value

    def box_width(self):
        width, height = self.drawer.max_layout_size(    
            [i.name for i in self.qtile.groups],
            self.font,
            self.fontsize
        )
        return width + self.padding*2 + self.margin_x*2 + self.borderwidth*2

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.setup_hooks()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.bar.draw()
        hook.subscribe.client_managed(hook_response)
        hook.subscribe.client_urgent_hint_changed(hook_response)
        hook.subscribe.client_killed(hook_response)
        hook.subscribe.setgroup(hook_response)
        hook.subscribe.group_window_add(hook_response)

    def drawbox(self, offset, text, color, width=None):
        layout = self.drawer.textlayout(text, self.foreground, self.font, self.fontsize)
        if width is not None:
            layout.width = width
        framed = layout.framed(self.borderwidth, color, self.padding, self.padding)
        framed.draw(offset, self.margin_y)


class AGroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = manager.Defaults(
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 3, "Current group border width"),
        ("font", "Monospace", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("foreground", "aaaaaa", "Active group font colour"),
        ("background", "000000", "Widget background"),
        ("border", "215578", "Border colour"),
        ("padding", 5, "Padding inside the box")
    )
    def click(self, x, y):
        self.bar.screen.group.cmd_nextgroup()

    def calculate_width(self):
        return self.box_width()

    def draw(self):
        self.drawer.clear(self.background)
        e = (i for i in self.qtile.groups if i.name == self.bar.screen.group.name ).next()
        self.drawbox(self.margin_x, e.name, self.border)
        self.drawer.draw()


class GroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = manager.Defaults(
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 3, "Current group border width"),
        ("font", "Monospace", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("foreground", "aaaaaa", "Active group font colour"),
        ("background", "000000", "Widget background"),

        ("this_screen_border", "215578", "Border colour for group on this screen."),
        ("other_screen_border", "404040", "Border colour for group on other screen."),

        ("padding", 5, "Padding inside the box")
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    def calculate_width(self):
        return self.box_width() * len(self.qtile.groups)

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        bw = self.box_width()
        self.drawer.clear(self.background)
        for i, g in enumerate(self.qtile.groups):
            if g.screen:
                if self.bar.screen.group.name == g.name:
                    border = self.this_screen_border
                else:
                    border = self.other_screen_border
            elif self.group_has_urgent(g):
                border = self.urgent_border
            else:
                border = self.background

            self.drawbox(
                self.margin_x + (bw*i),
                g.name,
                border,
                bw - self.margin_x*2 - self.padding*2
            )
        self.drawer.draw()


