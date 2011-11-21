import base
from .. import manager, bar, hook


class CurrentLayout(base._TextBox):
    defaults = manager.Defaults(
        ("font", "Arial", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("padding", None, "Padding left and right. Calculated if None."),
        ("background", None, "Background colour."),
        ("foreground", "#ffffff", "Foreground colour.")
    )

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self.bar.screen.group.layouts[0].name
        self.setup_hooks()

    def setup_hooks(self):
        def hook_response(layout):
            self.text = layout.name
            self.bar.draw()
        hook.subscribe.layout_change(hook_response)

