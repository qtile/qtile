from .. import bar, manager
import base


class TextBox(base._TextBox):
    """
        A flexible textbox that can be updated from bound keys, scripts and
        qsh.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None,
            "font shadow color, default is None(no shadow)"),
        ("padding", None, "Padding left and right. Calculated if None."),
        ("background", None, "Background colour."),
        ("foreground", "#ffffff", "Foreground colour.")
    )

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        """
            - text: Initial widget text.
            - width: An integer width, bar.STRETCH, or bar.CALCULATED .
        """
        base._TextBox.__init__(self, text, width, **config)

    def update(self, text):
        self.text = text
        self.bar.draw()

    def cmd_update(self, text):
        """
            Update the text in a TextBox widget.
        """
        self.update(text)

    def cmd_get(self):
        """
            Retrieve the text in a TextBox widget.
        """
        return self.text
