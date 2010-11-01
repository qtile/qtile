from .. import bar, utils, manager
import base

class Sep(base._Widget):
    """
        A visible widget separator.
    """
    defaults = manager.Defaults(
        ("padding", 2, "Padding on either side of separator."),
        ("linewidth", 1, "Width of separator line."),
        ("foreground", "888888", "Separator line colour."),
        ("background", "000000", "Background colour."),
        ("height_percent", 80, "Height as a percentage of bar height (0-100)."),
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.STATIC, **config)
        self.width = self.padding + self.linewidth

    def draw(self):
        self.drawer.clear(self.background)
        margin_top = (self.bar.height/float(100)*(100-self.height_percent)) / 2.0
        self.drawer.ctx.set_source_rgb(*utils.rgb(self.foreground))
        self.drawer.ctx.move_to(float(self.width)/2, margin_top) 
        self.drawer.ctx.line_to(float(self.width)/2, self.bar.height-margin_top)
        self.drawer.ctx.set_line_width(self.linewidth)
        self.drawer.ctx.stroke()
        self.drawer.draw()

