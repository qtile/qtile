import base

class WindowName(base._TextBox):
    def _configure(self, qtile, bar, event):
        base._Widget._configure(self, qtile, bar, event)
        self.event.subscribe("window_name_change", self.update)
        self.event.subscribe("focus_change", self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        self.text = w.name if w else " "
        self.draw()


