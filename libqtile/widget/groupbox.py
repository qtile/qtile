from .. import bar, hook, utils, manager
import cairo
import base

class GroupBox(base._Widget):
    """
        A widget that graphically displays the group list, indicating which
        groups have focus, and which groups contain clients.
    """
    defaults = manager.Defaults(
        ("padding_y", 2, "Y padding outside the box"),
        ("padding_x", 2, "X padding outside the box"),
        ("borderwidth", 3, "Current group border width."),
        ("font", "Monospace", "Font face"),
        ("active", "FFFFFF", "Active group font colour"),
        ("inactive", "404040", "Inactive group font colour"),
        ("background", "000000", "Widget background"),
        ("this_screen_border", "215578", "Border colour for group on this screen."),
        ("other_screen_border", "404040", "Border colour for group on other screen."),
        ("min_margin_x", 5, "Minimum X margin (inside the box).")
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    def click(self, x, y):
        return
        #groupOffset = x/self.boxwidth
        #if len(self.qtile.groups) - 1 >= groupOffset:
        #    self.bar.screen.setGroup(self.qtile.groups[groupOffset])

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
        self.width = self.boxwidth * len(self.qtile.groups)
        hook.subscribe("setgroup", self.draw)
        hook.subscribe("window_add", self.draw)
        self.setup_hooks()

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.background)
        for i, e in enumerate(self.qtile.groups):
            border = False
            if e.screen:
                if self.bar.screen.group.name == e.name:
                    border = self.this_screen_border
                else:
                    border = self.other_screen_border
            if border:
                self.drawer.ctx.set_source_rgb(*utils.rgb(border))
                self.drawer.rounded_rectangle(
                    (self.boxwidth * i) + self.padding_x, self.padding_y,
                    self.boxwidth - 2*self.padding_x,
                    self.bar.height - 2*self.padding_y,
                    self.borderwidth
                )
                self.drawer.ctx.stroke()

            # We could cache these...
            if e.windows:
                self.drawer.ctx.set_source_rgb(*utils.rgb(self.active))
            else:
                self.drawer.ctx.set_source_rgb(*utils.rgb(self.inactive))
            # We use the x_advance value rather than the width.
            _, _, _, y, x, _ = self.drawer.text_extents(e.name)
            self.drawer.ctx.move_to(
                (self.boxwidth*i) + self.boxwidth/2 - x/2,
                self.bar.height/2.0 + self.maxheight/2
            )
            self.drawer.ctx.show_text(
                e.name
            )
            self.drawer.ctx.stroke()
        self.drawer.draw()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.draw()
        hook.subscribe("client_new", hook_response)
        hook.subscribe("client_urgent_hint_changed", hook_response)
        hook.subscribe("client_killed", hook_response)

