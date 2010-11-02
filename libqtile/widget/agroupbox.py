from .. import bar, hook, utils, manager
import base

class AGroupBox(base._Widget):
    """
        A widget that graphically displays the current group.
    """
    defaults = manager.Defaults(
        ("padding_y", 3, "Y padding outside the box"),
        ("padding_x", 3, "X padding outside the box"),
        ("borderwidth", 3, "Current group border width"),
        ("font", "Monospace", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("foreground", "aaaaaa", "Active group font colour"),
        ("background", "000000", "Widget background"),
        ("border", "215578", "Border colour"),
        ("margin", 5, "Margin inside the box")
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    @property
    def fontsize(self):
        if self._fontsize is None:
            return self.bar.height - self.padding_y*2 - self.borderwidth*2 - self.margin*2
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value

    def click(self, x, y):
        self.bar.screen.group.cmd_nextgroup()

    def calculate_width(self):
        width, height = self.drawer.max_layout_size(    
            [i.name for i in self.qtile.groups],
            self.font,
            self.fontsize
        )
        return width + self.margin*2 + self.padding_x*2 + self.borderwidth*2

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.setup_hooks()

    def draw(self):
        self.drawer.clear(self.background)
        e = (i for i in self.qtile.groups if i.name == self.bar.screen.group.name ).next()
        layout = self.drawer.textlayout(e.name, self.foreground, self.font, self.fontsize)
        framed = layout.framed(self.borderwidth, self.border, self.margin, self.margin)
        framed.draw(
            self.padding_x,
            self.padding_y
        )
        self.drawer.draw()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.draw()
        hook.subscribe.client_managed(hook_response)
        hook.subscribe.client_urgent_hint_changed(hook_response)
        hook.subscribe.client_killed(hook_response)
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.group_window_add(self.draw)
