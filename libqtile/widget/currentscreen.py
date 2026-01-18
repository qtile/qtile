from libqtile import bar, hook
from libqtile.widget import base


class CurrentScreen(base._TextBox):
    """Indicates whether the screen this widget is on is currently active or not"""

    defaults = [
        ("active_text", "A", "Text displayed when the screen is active"),
        ("inactive_text", "I", "Text displayed when the screen is inactive"),
        ("active_color", "00ff00", "Color when screen is active"),
        ("inactive_color", "ff0000", "Color when screen is inactive"),
    ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(CurrentScreen.defaults)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.current_screen_change(self.update_text)
        self.update_text()

    def update_text(self):
        if self.qtile.current_screen == self.bar.screen:
            self.layout.colour = self.active_color
            self.update(self.active_text)
        else:
            self.layout.colour = self.inactive_color
            self.update(self.inactive_text)
