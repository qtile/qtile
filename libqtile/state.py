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
    """Represents the state of the qtile object

    Primarily used for restoring state across restarts; any additional state
    which doesn't fit nicely into X atoms can go here.
    """
    def __init__(self, qtile):
        # Note: window state is saved and restored via _NET_WM_STATE, so
        # the only thing we need to restore here is the layout and screen
        # configurations.
        self.groups = []
        self.screens = {}
        self.current_screen = 0
        self.scratchpads = {}
        self.orphans = []

        for group in qtile.groups:
            if isinstance(group, ScratchPad):
                self.scratchpads[group.name] = group.get_state()
                for dd in group.dropdowns.values():
                    dd.hide()
            else:
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
                orphans = group.restore_state(self.scratchpads.pop(group.name))
                self.orphans.extend(orphans)
        for sp_state in self.scratchpads.values():
            for _, pid, _ in sp_state:
                self.orphans.append(pid)
        if self.orphans:
            hook.subscribe.client_new(self.handle_orphan_dropdowns)

        qtile.focus_screen(self.current_screen)

    def handle_orphan_dropdowns(self, client):
        """
        Remove any windows from now non-existent scratchpad groups.
        """
        client_pid = client.window.get_net_wm_pid()
        if client_pid in self.orphans:
            self.orphans.remove(client_pid)
            client.group = None
            if not self.orphans:
                hook.unsubscribe.client_new(self.handle_orphan_dropdowns)
