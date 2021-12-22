# Copyright (c) 2012, Tycho Andersen. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from libqtile import hook
from libqtile.scratchpad import ScratchPad


class QtileState:
    """Represents the state of the Qtile object

    This is used for restoring state across restarts or config reloads.

    If `restart` is True, the current set of groups will be saved in the state. This is
    useful when restarting for Qtile version updates rather than reloading the config.
    ScratchPad groups are saved for both reloading and restarting.
    """

    def __init__(self, qtile, restart=True):
        self.groups = []
        self.screens = {}
        self.current_screen = 0
        self.scratchpads = {}
        self.orphans = []
        self.restart = restart  # True when restarting, False when config reloading

        for group in qtile.groups:
            if isinstance(group, ScratchPad):
                self.scratchpads[group.name] = group.get_state()
            elif restart:
                self.groups.append((group.name, group.layout.name, group.label))

        for index, screen in enumerate(qtile.screens):
            self.screens[index] = screen.group.name
            if screen == qtile.current_screen:
                self.current_screen = index

    def apply(self, qtile):
        """
        Rearrange the windows in the specified Qtile object according to this
        QtileState.
        """
        for (group, layout, label) in self.groups:
            try:
                qtile.groups_map[group].layout = layout
                qtile.groups_map[group].label = label
            except KeyError:
                qtile.add_group(group, layout, label=label)

        for (screen, group) in self.screens.items():
            try:
                group = qtile.groups_map[group]
                qtile.screens[screen].set_group(group)
            except (KeyError, IndexError):
                pass  # group or screen missing

        for group in qtile.groups:
            if isinstance(group, ScratchPad) and group.name in self.scratchpads:
                orphans = group.restore_state(self.scratchpads.pop(group.name), self.restart)
                self.orphans.extend(orphans)
        for sp_state in self.scratchpads.values():
            for _, wid, _ in sp_state:
                self.orphans.append(wid)
        if self.orphans:
            if self.restart:
                hook.subscribe.client_new(self.handle_orphan_dropdowns)
            else:
                for wid in self.orphans:
                    qtile.windows_map[wid].group = qtile.current_group

        qtile.focus_screen(self.current_screen)

    def handle_orphan_dropdowns(self, client):
        """
        Remove any windows from now non-existent scratchpad groups.
        """
        client_wid = client.wid
        if client_wid in self.orphans:
            self.orphans.remove(client_wid)
            client.group = None
            if not self.orphans:
                hook.unsubscribe.client_new(self.handle_orphan_dropdowns)
