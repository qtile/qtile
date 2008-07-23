import manager, window, config

class Gap:
    def __init__(self, width):
        self.width = width
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen):
        self.qtile, self.screen = qtile, screen

    def geometry(self):
        """
            Returns (x, y, width, height)
        """
        s = self.screen
        if s.top is self:
            return s.x, s.y, s.width, self.width
        elif s.bottom is self:
            return s.x, s.dy + s.dheight, s.width, self.width
        elif s.left is self:
            return s.x, s.dy, self.width, s.dheight
        elif s.right is self:
            return s.dx + s.dwidth, s.y + s.dy, self.width, s.dheight


class Bar(Gap):
    def __init__(self, widgets, width):
        Gap.__init__(self, width)
        self.widgets = widgets

    def _configure(self, qtile, screen):
        if not self in [screen.top, screen.bottom]:
            raise config.ConfigError("Bars must be at the top or the bottom of the screen.")
        Gap._configure(self, qtile, screen)
        self.window = window.Internal.create(
                            self.qtile,
                            *self.geometry()
                      )
        qtile.internalMap[self.window.window] = self.window
        self.window.unhide()


