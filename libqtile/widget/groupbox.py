from .. import bar, hook, utils
import cairo
import base

class GroupBox(base._Widget):
    PADDING_Y = 2           # Y padding outside the box
    PADDING_X = 2           # X padding outside the box
    BORDERWIDTH = 1

    FOREGROUND = "FFFFFF"
    BACKGROUND = "000000"
    THIS_SCREEN_BORDER = "0000ff"
    OTHER_SCREEN_BORDER = "404040"

    def click(self, x, y):
        return
        #groupOffset = x/self.boxwidth
        #if len(self.qtile.groups) - 1 >= groupOffset:
        #    self.bar.screen.setGroup(self.qtile.groups[groupOffset])

    def _configure(self, qtile, bar, theme):
        base._Widget._configure(self, qtile, bar, theme)
        self.drawer.set_font("Monospace", self.bar.height)
                
        # Leave a 10% margin
        self.margin_y = int((self.bar.height - (self.PADDING_Y + self.BORDERWIDTH)*2)*0.1)

        self.maxwidth, self.maxheight = self.drawer.fit_fontsize(
            [i.name for i in qtile.groups],
            self.bar.height - (self.PADDING_Y + self.margin_y + self.BORDERWIDTH)*2
        )
        self.margin_x = int(self.maxwidth * 0.1)
        self.boxwidth = self.maxwidth + self.PADDING_X*2 + self.BORDERWIDTH*2 + self.margin_x*2
        self.width = self.boxwidth * len(self.qtile.groups)
        hook.subscribe("setgroup", self.draw)
        hook.subscribe("window_add", self.draw)
        self.setup_hooks()

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.BACKGROUND)
        for i, e in enumerate(self.qtile.groups):
            border = False
            if e.screen:
                if self.bar.screen.group.name == e.name:
                    border = self.THIS_SCREEN_BORDER
                else:
                    border = self.OTHER_SCREEN_BORDER
            if border:
                self.drawer.ctx.set_source_rgb(*utils.rgb(border))
                self.drawer.rounded_rectangle(
                    (self.boxwidth * i) + self.PADDING_X, self.PADDING_Y,
                    self.boxwidth - 2*self.PADDING_X, self.bar.height - 2*self.PADDING_Y,
                    self.BORDERWIDTH
                )
                self.drawer.ctx.stroke()

            # We could cache these...
            self.drawer.ctx.set_source_rgb(*utils.rgb(self.FOREGROUND))
            _, _, x, y, _, _ = self.drawer.text_extents(e.name)
            self.drawer.ctx.move_to(
                (self.boxwidth * i) + (self.boxwidth - x)/2,
                self.maxheight + (self.bar.height - self.maxheight - self.margin_y)/2
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

