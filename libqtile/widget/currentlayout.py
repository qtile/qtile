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
    def __init__(self, width = bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        def hook_response(layout):
            self.text = layout.name
        hook.subscribe.layout_change(hook_response)

