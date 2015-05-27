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
from .base import SingleWindow


class Max(SingleWindow):
    """
        A simple layout that only displays one window at a time, filling the
        screen. This is suitable for use on laptops and other devices with
        small screens. Conceptually, the windows are managed as a stack, with
        commands to switch to next and previous windows in the stack.
    """
    defaults = [("name", "max", "Name of this layout.")]

    def __init__(self, **config):
        SingleWindow.__init__(self, **config)
        self.clients = []
        self.add_defaults(Max.defaults)
        self.current = None

    def _get_window(self):
        return self.current

    def focus(self, client):
        self.group.layoutAll()
        self.current = client

    def focus_first(self):
        if self.clients:
            return self.clients[0]

    def focus_last(self):
        if self.clients:
            return self.clients[-1]

    def focus_next(self, window):
        if not self.clients:
            return
        if window is None:
            return
        if window != self._get_window():
            self.focus(window)
        idx = self.clients.index(window)
        if idx + 1 < len(self.clients):
            return self.clients[idx + 1]

    def focus_previous(self, window):
        if not self.clients:
            return
        if window is None:
            return
        if window != self._get_window():
            self.focus(window)
        idx = self.clients.index(window)
        if idx > 0:
            return self.clients[idx - 1]

    def up(self):
        client = self.focus_previous(self.current) or self.focus_last()
        self.group.focus(client, False)

    def down(self):
        client = self.focus_next(self.current) or self.focus_first()
        self.group.focus(client, False)

    def clone(self, group):
        c = SingleWindow.clone(self, group)
        c.clients = []
        return c

    def add(self, client):
        try:
            idx = self.clients.index(self._get_window())
        except ValueError:
            self.clients.append(client)
        else:
            self.clients.insert(idx + 1, client)

    def remove(self, client):
        try:
            idx = self.clients.index(client)
        except ValueError:
            return
        else:
            del self.clients[idx]

        if client is self.current:
            try:
                # The previous client must become current
                # if idx == 0, using self.clients[-1] is indeed correct
                self.current = self.clients[idx - 1]
            except IndexError:
                self.current = None

        return self.current

    def configure(self, client, screen):
        if self.clients and client is self.current:
            client.place(
                screen.x,
                screen.y,
                screen.width,
                screen.height,
                0,
                None
            )
            client.unhide()
        else:
            client.hide()

    def info(self):
        d = SingleWindow.info(self)
        d["clients"] = [x.name for x in self.clients]
        return d

    def cmd_down(self):
        """
            Switch down in the window list.
        """
        self.down()

    cmd_next = cmd_down

    def cmd_up(self):
        """
            Switch up in the window list.
        """
        self.up()

    cmd_previous = cmd_up

    def get_state(self):
        d = SingleWindow.info(self)
        d["clients"] = [x.window.wid for x in self.clients]
        if self.current is not None:
            d["current"] = self.current.window.wid
        return d

    def restore_state(self, info, windowMap):
        self.clients = [windowMap[x] for x in info["clients"]]
        try:
            self.current = windowMap[info["current"]]
        except KeyError:  # No window is current
            pass
