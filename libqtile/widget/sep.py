from libqtile.widget import base


class Sep(base._Widget):
    """A visible widget separator"""

    orientations = base.ORIENTATION_BOTH
    defaults = [
        ("padding", 2, "Padding on either side of separator."),
        ("linewidth", 1, "Width of separator line."),
        ("foreground", "888888", "Separator line colour."),
        ("size_percent", 80, "Size as a percentage of bar size (0-100)."),
    ]

    def __init__(self, **config):
        length = config.get("padding", 2) * 2 + config.get("linewidth", 1)
        base._Widget.__init__(self, length, **config)
        self.add_defaults(Sep.defaults)
        self.length = self.padding + self.linewidth

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        margin = (self.bar.size / float(100) * (100 - self.size_percent)) / 2.0
        if self.bar.horizontal:
            self.drawer.draw_vbar(
                self.foreground,
                float(self.length) / 2,
                margin,
                self.bar.size - margin,
                linewidth=self.linewidth,
            )
        else:
            self.drawer.draw_hbar(
                self.foreground,
                margin,
                self.bar.size - margin,
                float(self.length) / 2,
                linewidth=self.linewidth,
            )
        self.draw_at_default_position()
