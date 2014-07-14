import base
from .. import bar, hook

import gobject


class Clipboard(base._TextBox):
    defaults = [
        ("selection", "CLIPBOARD",
            "the selection to display(CLIPBOARD or PRIMARY)"),
        ("max_width", 10, "size in pixels of task title"),
        ("timeout", 10,
            "Default timeout (seconds) for display text, None to keep forever")
        ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(Clipboard.defaults)
        self.timeout_id = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = ""
        self.setup_hooks()

    def clear(self, *args):
        self.text = ""
        self.bar.draw()

    def setup_hooks(self):
        def hook_change(name, selection):
            if name != self.selection:
                return
            text = selection["selection"].replace("\n", " ")
            text = text.strip()
            if len(text) > self.max_width:
                text = text[:self.max_width] + "..."
            self.text = text

            if self.timeout_id:
                gobject.source_remove(self.timeout_id)
                self.timeout_id = None

            if self.timeout:
                self.timeout_id = self.timeout_add(self.timeout, self.clear)
            self.bar.draw()

        def hook_notify(name, selection):
            if name != self.selection:
                return

            if self.timeout_id:
                gobject.source_remove(self.timeout_id)
                self.timeout_id = None

            # only clear if don't change don't apply in .5 seconds
            self.timeout_id = self.timeout_add(.5, self.clear)

        hook.subscribe.selection_notify(hook_notify)
        hook.subscribe.selection_change(hook_change)
