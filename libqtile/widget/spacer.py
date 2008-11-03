from .. import bar
import base

class Spacer(base._Widget):
    def _configure(self, qtile, barobj, event):
        base._Widget._configure(self, qtile, barobj, event)
        self.width = bar.STRETCH

    def draw(self):
        pass

