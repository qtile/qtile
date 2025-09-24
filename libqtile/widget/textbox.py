from typing import Any

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.widget import base


class TextBox(base._TextBox):
    """A flexible textbox that can be updated from bound keys, scripts, and qshell."""

    defaults: list[tuple[str, Any, str]] = [
        ("font", "sans", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None, "font shadow color, default is None(no shadow)"),
        ("padding", None, "Padding left and right. Calculated if None."),
        ("foreground", "#ffffff", "Foreground colour."),
    ]

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, text=text, width=width, **config)

    @expose_command()
    def get(self):
        """Retrieve the text in a TextBox widget"""
        return self.text

    @expose_command()
    def update(self, text):
        base._TextBox.update(self, text)
