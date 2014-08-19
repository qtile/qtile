from .. import bar
import base


class Spacer(base._Widget):
    """
        Just an empty space on the bar. Often used with width equal to
        bar.STRETCH to push bar widgets to the right edge of the screen.
    """
    def __init__(self, width=bar.STRETCH):
        """
            - width: Width of the widget.
              Can be either ``bar.STRETCH`` or a width in pixels.
        """
        base._Widget.__init__(self, width)

    def draw(self):
        self.drawer.clear(self.bar.background)
        self.drawer.draw(self.offset, self.width)
