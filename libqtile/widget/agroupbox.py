from .. import bar, hook, utils, manager
import base

class AGroupBox(base._Widget):
    """
        A widget that graphically displays just the current group.
    """
    defaults = manager.Defaults(
        ("padding_y", 2, "Y padding outside the box"),
        ("padding_x", 2, "X padding outside the box"),
        ("borderwidth", 3, "Current group border width."),
        ("font", "Terminus-Bold", "Font face"),
        ("foreground", "aaaaaa", "Active group font colour"),
        ("background", "000000", "Widget background"),
        ("border", "215578", "Border colour"),
        ("min_margin_x", 5, "Minimum X margin (inside the box).")
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    def click(self, x, y):
        self.bar.screen.group.cmd_nextgroup()

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.drawer.set_font(self.font, self.bar.height)
                
        # Leave a 10% margin top and bottom
        self.margin_y = int((self.bar.height - (self.padding_y + self.borderwidth)*2)*0.2)
        self.maxwidth, self.maxheight = self.drawer.fit_text(
            [i.name for i in qtile.groups],
            self.bar.height - (self.padding_y + self.margin_y + self.borderwidth)*2
        )
        self.margin_x = max(self.min_margin_x, int(self.maxwidth * 0.2))
        self.boxwidth = self.maxwidth + self.padding_x*2 + self.borderwidth*2 + self.margin_x*2
        self.width = self.boxwidth
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.group_window_add(self.draw)
        self.setup_hooks()

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.background)
        e = ( i for i in self.qtile.groups if i.name == self.bar.screen.group.name ).next()
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.border))
        self.drawer.rounded_rectangle(
            self.padding_x, self.padding_y,
            self.boxwidth - 2*self.padding_x,
            self.bar.height - 2*self.padding_y,
            self.borderwidth
        )
        self.drawer.ctx.stroke()

        self.drawer.ctx.set_source_rgb(*utils.rgb(self.foreground))
       # We use the x_advance value rather than the width.
        _, _, _, y, x, _ = self.drawer.text_extents(e.name)
        self.drawer.ctx.move_to(
         (self.boxwidth - x)/2, (self.bar.height + self.maxheight)/2 )
        self.drawer.ctx.show_text( e.name )
        self.drawer.ctx.stroke()
        self.drawer.draw()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.draw()
        hook.subscribe.client_managed(hook_response)
        hook.subscribe.client_urgent_hint_changed(hook_response)
        hook.subscribe.client_killed(hook_response)
