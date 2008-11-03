from .. import bar
import base

class TextBox(base._TextBox):
    def __init__(self, name, text=" ", width=bar.STRETCH,
                 foreground="white", background=bar._HIGHLIGHT, font=None):
        """
            :name Name for this widget.
            :text Initial widget text.
            :width Either an integer width, or the STRETCH constant.
            :foreground Foreground color.
            :background Background color.
            :font Font specification.
        """
        self.name = name
        base._TextBox.__init__(self, text, width, foreground, background, font)

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

