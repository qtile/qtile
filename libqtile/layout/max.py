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
from base import Layout
from .. import command, utils


class Max(Layout):
    name = "max"
    def __init__(self):
        Layout.__init__(self)
        self.clients = []

    def up(self):
        if self.clients:
            utils.shuffleUp(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], False)

    def down(self):
        if self.clients:
            utils.shuffleDown(self.clients)
            self.group.layoutAll()
            self.group.focus(self.clients[0], False)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.clients = []
        return c

    def add(self, c):
        self.clients.insert(0, c)
        self.group.focus(self.clients[0] if self.clients else None, False)

    def remove(self, c):
        self.clients.remove(c)
        self.group.focus(self.clients[0] if self.clients else None, False)

    def configure(self, c):
        if self.clients and c is self.clients[0]:
            c.place(
                self.group.screen.dx,
                self.group.screen.dy,
                self.group.screen.dwidth,
                self.group.screen.dheight,
                0,
                None
            )
            c.unhide()
        else:
            c.hide()

    def info(self):
        return [i.name for i in self.clients]

    def cmd_down(self):
        """
            Switch down in the window list.
        """
        self.down()

    def cmd_up(self):
        """
            Switch up in the window list.
        """
        self.up()

    def cmd_get(self):
        """
            Return list of window names in order, starting with the current
            window.
        """
        return self.info()
