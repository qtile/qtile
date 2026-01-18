from libqtile.widget.base import _TextBox


class ConfigErrorWidget(_TextBox):
    def __init__(self, **config):
        _TextBox.__init__(self, **config)
        self.class_name = self.widget.__class__.__name__
        self.text = f"Widget crashed: {self.class_name} (click to hide)"
        self.add_callbacks({"Button1": self._hide})

    def _hide(self):
        self.text = ""
        self.bar.draw()
