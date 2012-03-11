from .. import hook, bar, manager
import base


class WindowName(base._TextBox):
    """
        Displays the name of the window that currently has focus.
    """
    def __init__(self, width=bar.STRETCH, **config):
        base._TextBox.__init__(self, width=width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.window_name_change(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        state = ''
        if w is None:
            pass
        elif w.maximized:
            state = '[] '
        elif w.minimized:
            state = '_ '
        elif w.floating:
            state = 'V '
        self.text = "%s%s" % (state,  w.name if w and w.name else " ")
        self.bar.draw()
