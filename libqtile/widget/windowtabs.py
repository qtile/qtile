from .. import hook, bar, manager
import base


class WindowTabs(base._TextBox):
    """
        Displays the name of each window in the current group.
        The window that currently has focus is highlighted.
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Font face."),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("padding", None, "Padding left and right."),
        ("background", "000000", "Background colour."),
        ("foreground", "ffffff", "Foreground colour."),
        ("separator", " | ", "Task separator text."),
        ("selected", ("<", ">"), "Selected task indicator"),
    )

    def __init__(self, **config):
        base._TextBox.__init__(self, width=bar.STRETCH, **config)
        if not isinstance(self.selected, (tuple, list)):
            self.selected = (self.selected, self.selected)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.window_name_change(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)

    def button_press(self, x, y, button):
        self.bar.screen.group.cmd_next_window()

    def update(self):
        names = []
        for w in self.bar.screen.group.windows:
            state = ''
            if w is None:
                pass
            elif w.maximized:
                state = '[] '
            elif w.minimized:
                state = '_ '
            elif w.floating:
                state = 'V '
            task = "%s%s" % (state,  w.name if w and w.name else " ")
            if w is self.bar.screen.group.currentWindow:
                task = task.join(self.selected)
            names.append(task)
        self.text = self.separator.join(names)
        self.bar.draw()
