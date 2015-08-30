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
from . import window
import libqtile


class QtileState(object):
    """
        Represents the state of the qtile object. Primarily used for restoring
        state across restarts; any additional state which doesn't fit nicely
        into X atoms can go here.
    """
    def __init__(self, qtile):
        # Note: window state is saved and restored via _NET_WM_STATE, so
        # the only thing we need to restore here is the layout and screen
        # configurations.
        self.groups = {}
        self.screens = {}
        self.focus_history = {}
        self.current_screen = 0
        self.layout_map = {}

        for group in qtile.groups:
            self.groups[group.name] = group.layout.name
            self.layout_map[group.name] = {}
            for layout in group.layouts:
                self.save_layout(layout, group)
            self.focus_history[group.name] = group.focusHistory
        for index, screen in enumerate(qtile.screens):
            self.screens[index] = screen.group.name
            if screen == qtile.currentScreen:
                self.current_screen = index

    def save_layout(self, layout, group, save=True):

        if save:
            self.layout_map[group.name][layout.name] = layout
        layout.group = None                 # We Need this for serialization to work
        if isinstance(layout, libqtile.layout.slice.Slice):  # Special cases as they have layout objects within there structure
            self.save_layout(layout.fallback, group, False)
            self.save_layout(layout._slice, group, False)
        if isinstance(layout, libqtile.layout.tree.TreeTab):
            layout._draw = True if layout._panel is not None else False
            layout._drawer = None
            layout._panel = None
            layout._layout = None

    def restore_window(self, qtile, saved_layout, layout):  # Restore objects with references window objects

        members = dir(saved_layout)
        for member in members:
            try:
                x = getattr(saved_layout, member)
                if isinstance(x, list):
                    tmp = []
                    last = None
                    for i in x:
                        if isinstance(i, window.Window):
                            tmp.append(qtile.windowMap[i.wid])
                        else:
                            tmp.append(i)
                        last = i
                    if isinstance(last, window.Window):
                        setattr(layout, member, tmp)
                elif isinstance(x, window.Window):  # Add exception for unpickelable objects here
                    setattr(layout, member, qtile.windowMap[x.wid])  # we have to use qtile windowMap to fully restore the window state
                elif not callable(x) and not str.startswith(member, '_') and not isinstance(x, libqtile.base.Layout):
                    setattr(layout, member, x)
            except AttributeError:
                pass

    def restore_layout(self, qtile, saved_layout, layout, group):  # Restore layout objects

        saved_layout.group = group
        self.restore_window(qtile, saved_layout, layout)
        if isinstance(layout, libqtile.layout.tree.TreeTab):
            layout._tree = saved_layout._tree
            layout._nodes = saved_layout._nodes
            for i in saved_layout._nodes:
                layout._nodes[i].window = qtile.windowMap[i]
            if hasattr(saved_layout, '_draw') and saved_layout._draw:
                layout._create_panel()
                screen = layout.group.screen.get_rect()
                layout.show(screen)
        if isinstance(layout, libqtile.layout.stack.Stack):
            for i in range(len(layout.stacks)):
                self.restore_window(qtile, saved_layout.stacks[i], layout.stacks[i])  # Objects with references to window objects
        if isinstance(layout, libqtile.layout.slice.Slice):
            self.restore_layout(qtile, saved_layout._slice, layout._slice, group)  # layout with references to layout objects
            self.restore_layout(qtile, saved_layout.fallback, layout.fallback, group)

    def apply(self, qtile):
        """
            Rearrange the windows in the specified Qtile object according to
            this QtileState.
        """
        try:
            for group in qtile.groups:
                group.focusHistory = [qtile.windowMap[i.wid] for i in self.focus_history[group.name]]
                for layout in group.layouts:
                    self.restore_layout(qtile, self.layout_map[group.name][layout.name], layout, group)
        except KeyError:
            pass  # group missing

        for (group, layout) in self.groups.items():
            try:
                qtile.groupMap[group].layout = layout
            except KeyError:
                pass  # group missing

        for (screen, group) in self.screens.items():
            try:
                group = qtile.groupMap[group]
                qtile.screens[screen].setGroup(group)
            except (KeyError, IndexError):
                pass  # group or screen missing
        qtile.toScreen(self.current_screen)
