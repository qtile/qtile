from .. import bar
import base

class TextBox(base._TextBox):
    defaults = dict(
        font = "Monospace",
    )
    def __init__(self, name, text=" ", width=bar.STRETCH, **attrs):
        """
            :name Name for this widget.
            :text Initial widget text.
            :width Either an integer width, or the STRETCH constant.
        """
        self.name = name
        base._TextBox.__init__(self, text, width, **attrs)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.drawer.set_font(self.font, self.bar.height)

    def update(self, text):
        self.text = text
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

