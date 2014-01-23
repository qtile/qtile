from .. import bar
import base


class Sep(base._Widget):
    """
        A visible widget separator.
    """
    defaults = [
        ("padding", 2, "Padding on either side of separator."),
        ("linewidth", 1, "Width of separator line."),
        ("foreground", "888888", "Separator line colour."),
        (
            "height_percent",
            80,
            "Height as a percentage of bar height (0-100)."
        ),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.STATIC, **config)
        self.add_defaults(Sep.defaults)
        self.width = self.padding + self.linewidth

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        margin_top = (
            self.bar.height / float(100) * (100 - self.height_percent)) / 2.0
        self.drawer.draw_vbar(
            self.foreground,
            float(self.width) / 2,
            margin_top,
            self.bar.height - margin_top,
            linewidth=self.linewidth
        )
        self.drawer.draw(self.offset, self.width)
