from libqtile import bar
from libqtile.widget import base


class Spacer(base._Widget):
    """Just an empty space on the bar

    Often used with length equal to bar.STRETCH to push bar widgets to the
    right or bottom edge of the screen.

    Parameters
    ==========
    length :
        Length of the widget.  Can be either ``bar.STRETCH`` or a length in
        pixels.
    width :
        DEPRECATED, same as ``length``.
    """

    orientations = base.ORIENTATION_BOTH
    defaults = [("background", None, "Widget background color")]

    def __init__(self, length=bar.STRETCH, **config):
        """ """
        base._Widget.__init__(self, length, **config)
        self.add_defaults(Spacer.defaults)

    def draw(self):
        if self.length > 0:
            self.drawer.clear(self.background or self.bar.background)
            self.draw_at_default_position()
