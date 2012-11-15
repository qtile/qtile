from .. import bar
import base


class Spacer(base._Widget):
    """
        Just an empty space on the bar. Often used with width equal to
        bar.STRETCH to push bar widgets to the right edge of the screen.
    """
    def __init__(self, width=bar.STRETCH):
        """
            - width: bar.STRETCH, or a pixel width.
        """
        base._Widget.__init__(self, width)

    def draw(self):
        self.clear()
        self.drawer.draw(self.offset, self.width)
