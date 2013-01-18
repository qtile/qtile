# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import copy
from .. import command, configurable

class Layout(command.CommandObject, configurable.Configurable):
    """
        This class defines the API that should be exposed by all layouts.
    """
    @classmethod
    def _name(cls):
        return cls.__class__.__name__.lower()

    defaults = [
        ("name", None, "The name of this layout"
            "(usually the class' name in lowercase, e.g. 'max'"),
    ]

    def __init__(self, **config):
        # name is a little odd; we can't resolve it until the class is defined
        # (i.e., we can't figure it out to define it in Layout.defaults), so
        # we resolve it here instead.
        if "name" not in config:
            config["name"] = self.__class__.__name__.lower()

        command.CommandObject.__init__(self)
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Layout.defaults)

    def layout(self, windows, screen):
        assert windows, "let's eliminate unnecessary calls"
        for i in windows:
            self.configure(i, screen)

    def clone(self, group):
        """
            :group Group to attach new layout instance to.

            Make a copy of this layout. This is done to provide each group with
            a unique instance of every layout.
        """
        c = copy.copy(self)
        c.group = group
        return c

    def focus(self, c):
        """
            Called whenever the focus changes.
        """
        pass

    def blur(self):
        """
            Called whenever focus is gone from this layout.
        """
        pass

    def add(self, c):
        """
            Called whenever a window is added to the group, whether the layout
            is current or not. The layout should just add the window to its
            internal datastructures, without mapping or configuring.
        """
        pass

    def remove(self, c):
        """
            Called whenever a window is removed from the group, whether the
            layout is current or not. The layout should just de-register the
            window from its data structures, without unmapping the window.

            Returns the "next" window that should gain focus or None.
        """
        pass

    def configure(self, c, screen):
        """
            This method should:

                - Configure the dimensions and borders of a window using the
                  .place() method.
                - Call either .hide or .unhide on the window.
        """
        raise NotImplementedError

    def info(self):
        """
            Returns a dictionary of layout information.
        """
        return dict(
            name=self.name,
            group=self.group.name
        )

    def _items(self, name):
        if name == "screen":
            return True, None
        elif name == "group":
            return True, None

    def _select(self, name, sel):
        if name == "screen":
            return self.group.screen
        elif name == "group":
            return self.group

    def cmd_info(self):
        """
            Return a dictionary of info for this object.
        """
        return self.info()

    def show(self, screen):
        """
            Called when layout is being shown
        """

    def hide(self):
        """
            Called when layout is being hidden
        """


class SingleWindow(Layout):
    """Base for layouts with single visible window"""

    def __init__(self, **config):
        Layout.__init__(self, **config)

    def _get_window(self):
        """Should return either visible window or None"""
        raise NotImplementedError("abstract method")

    def configure(self, win, screen):
        if win is self._get_window():
            win.place(
                screen.x, screen.y,
                screen.width, screen.height,
                0,
                None,
                )
            win.unhide()
        else:
            win.hide()

    def remove(self, win):
        cli = self.clients.pop(0)
        if cli == win:
            return self.clients[0]

    def focus_first(self):
        return self._get_window()

    def focus_next(self, win):
        return None

    def focus_last(self):
        return self._get_window()

    def focus_prev(self, win):
        return None


class Delegate(Layout):
    """Base for all delegation layouts"""

    def __init__(self, **config):
        self.layouts = {}
        Layout.__init__(self, **config)

    def clone(self, group):
        c = Layout.clone(group)
        c.layouts = {}
        return c

    def _get_layouts(self):
        """Returns all children layouts"""
        raise NotImplementedError("abstact method")

    def _get_active_layout(self):
        """Returns layout to which delegate commands to"""
        raise NotImplementedError("abstrac method")

    def delegate_layout(self, windows, mapping):
        """Delegates layouting actual windows

        :param windows: windows to layout
        :param mapping: mapping from layout to ScreenRect for each layout
        """
        grouped = {}
        for w in windows:
            lay = self.layouts[w]
            if lay in grouped:
                grouped[lay].append(w)
            else:
                grouped[lay] = [w]
        for lay, wins in grouped.iteritems():
            lay.layout(wins, mapping[lay])

    def remove(self, win):
        lay = self.layouts.pop(win)
        focus = lay.remove(win)
        if not focus:
            layouts = self._get_layouts()
            idx = layouts.index(lay)
            while idx < len(layouts) - 1 and not focus:
                idx += 1
                focus = layouts[idx].focus_first()
        return focus

    def focus_first(self):
        layouts = self._get_layouts()
        for lay in layouts:
            win = lay.focus_first()
            if win:
                return win

    def focus_last(self):
        layouts = self._get_layouts()
        for lay in reversed(layouts):
            win = lay.focus_last()
            if win:
                return win

    def focus_next(self, win):
        layouts = self._get_layouts()
        cur = self.layouts[win]
        focus = cur.focus_next(win)
        if not focus:
            idx = layouts.index(cur)
            while idx < len(layouts) - 1 and not focus:
                idx += 1
                focus = layouts[idx].focus_first()
        return focus

    def focus_prev(self, win):
        layouts = self._get_layouts()
        cur = self.layouts[win]
        focus = cur.focus_prev(win)
        if not focus:
            idx = layouts.index(cur)
            while idx > 0 and not focus:
                idx -= 1
                focus = layouts[idx].focus_last()
        return focus

    def cmd_up(self):
        self._get_active_layout().cmd_up()

    def cmd_down(self):
        self._get_active_layout().cmd_down()
