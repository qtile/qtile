from .. import bar
import base

class TextBox(base._TextBox):
    defaults = dict(
        font = "Monospace",
        fontsize = None,
        padding = None,
        background = None,
        foreground = "#ffffff"
    )
    def __init__(self, name, text=" ", width=bar.CALCULATED, **attrs):
        """
            :name Name for this widget.
            :text Initial widget text.
            :width An integer width, STRETCH, or CALCULATED .
        """
        self.name = name
        base._TextBox.__init__(self, text, width, **attrs)

    def update(self, text):
        self.text = text
        if self.width_type == bar.CALCULATED:
            self.guess_width()
        self.draw()

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

