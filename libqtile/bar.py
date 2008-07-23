import manager, window

class Bar(manager.Gap):
    def __init__(self, widgets, width):
        manager.Gap.__init__(self, width)
        self.widgets = widgets

    def _configure(self, qtile, screen):
        manager.Gap._configure(self, qtile, screen)
        self.window = window.Internal.create(
                            self.qtile,
                            *self.geometry()
                      )
        self.window.place(*self.geometry())
        self.window.unhide()


