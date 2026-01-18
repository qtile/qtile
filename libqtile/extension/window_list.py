from libqtile.backend import base
from libqtile.extension.dmenu import Dmenu
from libqtile.scratchpad import ScratchPad


class WindowList(Dmenu):
    """
    Give vertical list of all open windows in dmenu. Switch to selected.
    """

    defaults = [
        ("item_format", "{group}.{id}: {window}", "the format for the menu items"),
        (
            "all_groups",
            True,
            "If True, list windows from all groups; otherwise only from the current group",
        ),
        ("dmenu_lines", "80", "Give lines vertically. Set to None get inline"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(WindowList.defaults)

    def list_windows(self):
        id = 0
        self.item_to_win = {}

        if self.all_groups:
            windows = [w for w in self.qtile.windows_map.values() if isinstance(w, base.Window)]
        else:
            windows = self.qtile.current_group.windows

        for win in windows:
            if win.group and not isinstance(win.group, ScratchPad):
                item = self.item_format.format(
                    group=win.group.label or win.group.name, id=id, window=win.name
                )
                self.item_to_win[item] = win
                id += 1

    def run(self):
        self.list_windows()
        out = super().run(items=self.item_to_win.keys())

        try:
            sout = out.rstrip("\n")
        except AttributeError:
            # out is not a string (for example it's a Popen object returned
            # by super(WindowList, self).run() when there are no menu items to
            # list
            return

        try:
            win = self.item_to_win[sout]
        except KeyError:
            # The selected window got closed while the menu was open?
            return

        screen = self.qtile.current_screen
        screen.set_group(win.group)
        win.group.focus(win)
