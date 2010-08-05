from .. import bar, hook
import cairo
import base

class GroupBox(base._Widget):
    PADDING_Y = 2           # Y padding outside the box
    PADDING_X = 2           # X padding outside the box
    MARGIN_Y = 2            # Y padding between box and lettering
    MARGIN_X = 2            # X padding between box and lettering
    BORDERWIDTH = 1

    def click(self, x, y):
        return
        #groupOffset = x/self.boxwidth
        #if len(self.qtile.groups) - 1 >= groupOffset:
        #    self.bar.screen.setGroup(self.qtile.groups[groupOffset])

    def _configure(self, qtile, bar, theme):
        base._Widget._configure(self, qtile, bar, theme)
        self.drawer.set_font("Monospace", self.bar.height)
        self.maxwidth, self.maxheight = self.drawer.fit_fontsize(
            [i.name for i in qtile.groups],
            self.bar.height - (self.PADDING_Y + self.MARGIN_Y + self.BORDERWIDTH)*2
        )
        self.boxwidth = self.maxwidth + self.PADDING_X*2 + self.BORDERWIDTH*2 + self.MARGIN_X*2
        self.width = self.boxwidth * len(self.qtile.groups)
        hook.subscribe("setgroup", self.draw)
        hook.subscribe("window_add", self.draw)
        self.setup_hooks()

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        for i, e in enumerate(self.qtile.groups):
            self.drawer.ctx.set_source_rgb(1, 1, 1)
            self.drawer.ctx.rectangle(
                (self.boxwidth * i) + self.PADDING_X, self.PADDING_Y,
                self.boxwidth - 2*self.PADDING_X, self.bar.height - 2*self.PADDING_Y
            )
            # We could cache these...
            _, _, x, y, _, _ = self.drawer.text_extents(e.name)
            self.drawer.ctx.move_to(
                (self.boxwidth * i) + (self.boxwidth - x - self.MARGIN_X*2)/2,
                self.maxheight + (self.bar.height - self.maxheight - self.MARGIN_Y*2)/2
            )
            self.drawer.ctx.show_text(e.name)
            self.drawer.ctx.stroke()
        self.drawer.draw()

    def setup_hooks(self):
        draw = self.draw
        def hook_response(*args, **kwargs):
            self.draw()
        hook.subscribe("client_new", hook_response)
        hook.subscribe("client_urgent_hint_changed", hook_response)
        hook.subscribe("client_killed", hook_response)

