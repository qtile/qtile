import libqtile.layout
from libqtile import hook
from libqtile.lazy import lazy
from libqtile.widget import TextBox


class ScreenSplit(TextBox):
    """
    A simple widget to show the name of the current split and layout for the
    ``ScreenSplit`` layout.
    """

    defaults = [("format", "{split_name} ({layout})", "Format string.")]

    def __init__(self, **config):
        TextBox.__init__(self, "", **config)
        self.add_defaults(ScreenSplit.defaults)
        self.add_callbacks(
            {
                "Button4": lazy.layout.previous_split().when(layout="screensplit"),
                "Button5": lazy.layout.next_split().when(layout="screensplit"),
            }
        )
        self._drawn = False

    def _configure(self, qtile, bar):
        TextBox._configure(self, qtile, bar)
        self._set_hooks()

    def _set_hooks(self):
        hook.subscribe.layout_change(self._update)

    def _update(self, layout, group):
        if not self.configured:
            return

        if isinstance(layout, libqtile.layout.ScreenSplit) and group is self.bar.screen.group:
            split_name = layout.active_split.name
            layout_name = layout.active_layout.name
            self.set_text(split_name, layout_name)
        else:
            self.clear()

    def set_text(self, split_name, layout):
        self.update(self.format.format(split_name=split_name, layout=layout))

    def clear(self):
        self.update("")

    def finalize(self):
        hook.unsubscribe.layout_change(self._update)
        TextBox.finalize(self)

    def draw(self):
        # Force the widget to check layout the first time it's drawn
        if not self._drawn:
            self._update(self.bar.screen.group.layout, self.bar.screen.group)
            self._drawn = True
            return

        TextBox.draw(self)
