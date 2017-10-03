# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# Copyright (c) 2017 Dirk Hartmann
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
import six
from abc import ABCMeta, abstractmethod

from .. import command, configurable


@six.add_metaclass(ABCMeta)
class Layout(command.CommandObject, configurable.Configurable):
    """This class defines the API that should be exposed by all layouts"""
    @classmethod
    def _name(cls):
        return cls.__class__.__name__.lower()

    defaults = [(
        "name",
        None,
        "The name of this layout"
        " (usually the class' name in lowercase, e.g. 'max')"
    )]

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

    def finalize(self):
        pass

    def clone(self, group):
        """Duplicate a layout

        Make a copy of this layout. This is done to provide each group with a
        unique instance of every layout.

        Parameters
        ==========
        group:
            Group to attach new layout instance to.
        """
        c = copy.copy(self)
        c.group = group
        return c

    def _items(self, name):
        if name == "screen":
            return (True, None)
        elif name == "group":
            return (True, None)

    def _select(self, name, sel):
        if name == "screen":
            return self.group.screen
        elif name == "group":
            return self.group

    def show(self, screen):
        """Called when layout is being shown"""
        pass

    def hide(self):
        """Called when layout is being hidden"""
        pass

    def focus(self, client):
        """Called whenever the focus changes"""
        pass

    def blur(self):
        """Called whenever focus is gone from this layout"""
        pass

    def info(self):
        """Returns a dictionary of layout information"""
        return dict(
            name=self.name,
            group=self.group.name if self.group else None
        )

    def cmd_info(self):
        """Return a dictionary of info for this object"""
        return self.info()

    @abstractmethod
    def add(self, client):
        """Called whenever a window is added to the group

        Called whether the layout is current or not. The layout should just add
        the window to its internal datastructures, without mapping or
        configuring.
        """
        pass

    @abstractmethod
    def remove(self, client):
        """Called whenever a window is removed from the group

        Called whether the layout is current or not. The layout should just
        de-register the window from its data structures, without unmapping the
        window.

        Returns the "next" window that should gain focus or None.
        """
        pass

    @abstractmethod
    def configure(self, client, screen):
        """Configure the layout

        This method should:

            - Configure the dimensions and borders of a window using the
              `.place()` method.
            - Call either `.hide()` or `.unhide()` on the window.
        """
        pass

    @abstractmethod
    def focus_first(self):
        """Called when the first client in Layout shall be focused.

        This method should:
            - Return the first client in Layout, if any.
            - Not focus the client itself, this is done by caller.
        """
        pass

    @abstractmethod
    def focus_last(self):
        """Called when the last client in Layout shall be focused.

        This method should:
            - Return the last client in Layout, if any.
            - Not focus the client itself, this is done by caller.
        """
        pass

    @abstractmethod
    def focus_next(self, win):
        """Called when the next client in Layout shall be focused.

        This method should:
            - Return the next client in Layout, if any.
            - Return None if the next client would be the first client.
            - Not focus the client itself, this is done by caller.

        Do not implement a full cycle here, because the Groups cycling relies
        on returning None here if the end of Layout is hit,
        such that Floating clients are included in cycle.

        Parameters
        ==========
        win:
            The currently focused client.
        """
        pass

    @abstractmethod
    def focus_previous(self, win):
        """Called when the previous client in Layout shall be focused.

        This method should:
            - Return the previous client in Layout, if any.
            - Return None if the previous client would be the last client.
            - Not focus the client itself, this is done by caller.

        Do not implement a full cycle here, because the Groups cycling relies
        on returning None here if the end of Layout is hit,
        such that Floating clients are included in cycle.

        Parameters
        ==========
        win:
            The currently focused client.
        """
        pass

    @abstractmethod
    def cmd_next(self):
        pass

    @abstractmethod
    def cmd_previous(self):
        pass


class SingleWindow(Layout):
    """Base for layouts with single visible window"""

    def __init__(self, **config):
        Layout.__init__(self, **config)

    @abstractmethod
    def _get_window(self):
        """Should return either visible window or None"""
        pass

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


class Delegate(Layout):
    """Base for all delegation layouts"""

    def __init__(self, **config):
        self.layouts = {}
        Layout.__init__(self, **config)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.layouts = {}
        return c

    @abstractmethod
    def _get_layouts(self):
        """Returns all children layouts"""
        pass

    @abstractmethod
    def _get_active_layout(self):
        """Returns layout to which delegate commands to"""
        pass

    def delegate_layout(self, windows, mapping):
        """Delegates layouting actual windows

        Parameterer
        ===========
        windows:
            windows to layout
        mapping:
            mapping from layout to ScreenRect for each layout
        """
        grouped = {}
        for w in windows:
            lay = self.layouts[w]
            if lay in grouped:
                grouped[lay].append(w)
            else:
                grouped[lay] = [w]
        for lay, wins in grouped.items():
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

    def focus_previous(self, win):
        layouts = self._get_layouts()
        cur = self.layouts[win]
        focus = cur.focus_previous(win)
        if not focus:
            idx = layouts.index(cur)
            while idx > 0 and not focus:
                idx -= 1
                focus = layouts[idx].focus_last()
        return focus

    def __getattr__(self, name):
        """Delegate unimplemented command calls to active layout.

        For ``cmd_``-methods that don't exist on the Delegate subclass, this
        looks for an implementation on the active layout.
        """
        if name.startswith('cmd_'):
            return getattr(self._get_active_layout(), name)
        return super(Delegate, self).__getattr__(name)

    def info(self):
        d = Layout.info(self)
        for layout in self._get_layouts():
            d[layout.name] = layout.info()
        return d


class _ClientList(object):
    """
    ClientList maintains a list of clients and a current client.

    The collection is meant as a base or utility class for special layouts,
    which need to maintain one or several collections of windows, for example
    Columns or Stack, which use this class as base for their internal helper.

    The property 'current_index' get and set the index to the current client,
    whereas 'current_client' property can be used with clients directly.

    The collection implements focus_xxx methods as desired for Group.
    """

    def __init__(self):
        self._current_idx = 0
        self.clients = []

    @property
    def current_index(self):
        return self._current_idx

    @current_index.setter
    def current_index(self, x):
        if len(self):
            self._current_idx = abs(x % len(self))
        else:
            self._current_idx = 0
        return self._current_idx

    @property
    def current_client(self):
        if not self.clients:
            return None
        return self.clients[self._current_idx]

    @current_client.setter
    def current_client(self, client):
        self._current_idx = self.clients.index(client)

    def focus(self, client):
        """
        Mark the given client as the current focused client in collection.
        This is equivalent to setting current_client.
        """
        self.current_client = client

    def focus_first(self):
        """
        Returns the first client in collection.
        """
        return self[0]

    def focus_next(self, win):
        """
        Returns the client next from win in collection.
        """
        try:
            return self[self.index(win) + 1]
        except IndexError:
            return None

    def focus_last(self):
        """
        Returns the last client in collection.
        """
        return self[-1]

    def focus_previous(self, win):
        """
        Returns the client previous to win in collection.
        """
        try:
            idx = self.index(win)
        except IndexError:
            return None
        else:
            if idx > 0:
                return self[idx - 1]

    def add(self, client, offset_to_current=0):
        """
        Insert the given client into collection at position of the current.

        Use parameter 'offset_to_current' to specify where the client shall be
        inserted. Defaults to zero, which means at position of current client.
        Positive values are after the client.
        """
        pos = max(0, self._current_idx + offset_to_current)
        if pos < len(self.clients):
            self.clients.insert(pos, client)
        else:
            self.clients.append(client)

    def appendHead(self, client):
        """
        Append the given client in front of list.
        """
        self.clients.insert(0, client)

    def append(self, client):
        """
        Append the given client to the end of the collection.
        """
        self.clients.append(client)

    def remove(self, client):
        """
        Remove the given client from collection.
        """
        if client not in self.clients:
            return
        idx = self.clients.index(client)
        del self.clients[idx]
        if len(self) == 0:
            self._current_idx = 0
        elif idx <= self._current_idx:
            self._current_idx = max(0, self._current_idx - 1)

    def rotate_up(self, maintain_index=True):
        """
        Rotate the list. The first client is moved to last position.
        If maintain_index is True the current_index is adjusted,
        such that the same client stays current and goes up in list.
        """
        if len(self.clients) > 1:
            self.clients.append(self.clients.pop(0))
            if maintain_index:
                self.current_index -= 1

    def rotate_down(self, maintain_index=True):
        """
        Rotate the list. The last client is moved to first position.
        If maintain_index is True the current_index is adjusted,
        such that the same client stays current and goes down in list.
        """
        if len(self.clients) > 1:
            self.clients.insert(0, self.clients.pop())
            if maintain_index:
                self.current_index += 1

    def swap(self, c1, c2, focus=1):
        """
        Swap the two given clients in list.
        The optional argument 'focus' can be 1, 2 or anything else.
        In case of 1, the first client c1 is focused, in case of 2 the c2 and
        the current_index is not changed otherwise.
        """
        i1 = self.clients.index(c1)
        i2 = self.clients.index(c2)
        self.clients[i1], self.clients[i2] = self.clients[i2], self.clients[i1]
        if focus == 1:
            self.current_index = i1
        elif focus == 2:
            self.current_index = i2

    def shuffle_up(self, maintain_index=True):
        """
        Shuffle the list. The current client swaps position with its predecessor.
        If maintain_index is True the current_index is adjusted,
        such that the same client stays current and goes up in list.
        """
        idx = self._current_idx
        if idx > 0:
            self.clients[idx], self.clients[idx - 1] = self[idx - 1], self[idx]
            if maintain_index:
                self.current_index -= 1

    def shuffle_down(self, maintain_index=True):
        """
        Shuffle the list. The current client swaps position with its successor.
        If maintain_index is True the current_index is adjusted,
        such that the same client stays current and goes down in list.
        """
        idx = self._current_idx
        if idx + 1 < len(self.clients):
            self.clients[idx], self.clients[idx + 1] = self[idx + 1], self[idx]
            if maintain_index:
                self.current_index += 1

    def join(self, other, offset_to_current=0):
        """
        Add clients from 'other' _WindowCollection to self.
        'offset_to_current' works as described for add()
        """
        pos = max(0, self.current_index + offset_to_current)
        if pos < len(self.clients):
            self.clients = (self.clients[:pos:] + other.clients +
                            self.clients[pos::])
        else:
            self.clients.extend(other.clients)

    def index(self, client):
        return self.clients.index(client)

    def __len__(self):
        return len(self.clients)

    def __getitem__(self, i):
        try:
            return self.clients[i]
        except IndexError:
            return None

    def __iter__(self):
        return self.clients.__iter__()

    def __contains__(self, client):
        return client in self.clients

    def __str__(self):
        curr = self.current_client
        return "_WindowCollection: " + ", ".join(
            [('[%s]' if c == curr else '%s') % c.name for c in self.clients])

    def info(self):
        return dict(
            clients=[c.name for c in self.clients],
            current=self._current_idx,
        )

class _SimpleLayoutBase(Layout):
    """
    Basic layout class for simple layouts,
    which need to maintain a single list of clients.
    This class offers full fledged list of clients and focus cycling.

    Basic Layouts like Max and Matrix are based on this class
    """

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.clients = _ClientList()

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = _ClientList()
        return c

    def focus(self, client):
        self.clients.current_client = client
        self.group.layoutAll()

    def focus_first(self):
        return self.clients.focus_first()

    def focus_last(self):
        return self.clients.focus_last()

    def focus_next(self, window):
        return self.clients.focus_next(window)

    def focus_previous(self, window):
        return self.clients.focus_previous(window)

    def previous(self):
        client = self.focus_previous(self.clients.current_client) or self.focus_last()
        self.group.focus(client, True)

    def next(self):
        client = self.focus_next(self.clients.current_client) or self.focus_first()
        self.group.focus(client, True)

    def add(self, client, offset_to_current=0):
        return self.clients.add(client, offset_to_current)

    def remove(self, client):
        return self.clients.remove(client)

    def info(self):
        d = Layout.info(self)
        d.update(self.clients.info())
        return d
