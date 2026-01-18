from libqtile import bar, hook, pangocffi
from libqtile.log_utils import logger
from libqtile.widget import base


class WindowTabs(base._TextBox):
    """
    Displays the name of each window in the current group.
    Contrary to TaskList this is not an interactive widget.
    The window that currently has focus is highlighted.
    """

    defaults = [
        ("separator", " | ", "Task separator text."),
        ("selected", ("<b>", "</b>"), "Selected task indicator"),
        (
            "parse_text",
            lambda window_name: window_name,
            "Function to modify window names. It must accept "
            "a string argument (original window name) and return "
            "a string with the modified name.",
        ),
    ]

    def __init__(self, **config):
        width = config.pop("width", bar.STRETCH)
        base._TextBox.__init__(self, width=width, **config)
        self.add_defaults(WindowTabs.defaults)
        if not isinstance(self.selected, tuple | list):
            self.selected = (self.selected, self.selected)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.client_name_updated(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)
        self.add_callbacks({"Button1": self.bar.screen.group.next_window})

    def update(self, *args):
        names = []
        for w in self.bar.screen.group.windows:
            try:
                name = self.parse_text(w.name if w and w.name else "")
            except:  # noqa: E722
                logger.exception("parse_text function failed:")
                name = w.name if w and w.name else "(unnamed)"
            state = ""
            if w.maximized:
                state = "[] "
            elif w.minimized:
                state = "_ "
            elif w.floating:
                state = "V "
            task = pangocffi.markup_escape_text(state + name)
            if w is self.bar.screen.group.current_window:
                task = task.join(self.selected)
            names.append(task)
        self.text = self.separator.join(names)
        self.bar.draw()
