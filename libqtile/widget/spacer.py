from .. import bar, obj
import base

class Spacer(base._Widget):
    """
        Just an empty space on the bar. Often used with width equal to
        obj.STRETCH to push bar widgets to the right edge of the screen.
    """
    def __init__(self, width=obj.STRETCH):
        """
            - width: obj.STRETCH, or a pixel width.
        """
        base._Widget.__init__(self, width)

    def draw(self):
        self.drawer.clear(self.bar.background)
        self.drawer.draw(self.offset, self.width)
