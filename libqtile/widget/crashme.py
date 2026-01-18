from libqtile import bar
from libqtile.widget import base


class _CrashMe(base._TextBox):
    """A developer widget to force a crash in qtile

    Pressing left mouse button causes a zero divison error.  Pressing the right
    mouse button causes a cairo draw error.

    Parameters
    ==========

    width :
        A fixed width, or bar.CALCULATED to calculate the width automatically
        (which is recommended).
    """

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "Crash me !", width, **config)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font, self.fontsize, self.fontshadow, markup=True
        )

    def button_press(self, x, y, button):
        if button == 1:
            1 / 0
