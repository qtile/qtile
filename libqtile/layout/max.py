# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# Copyright (c) 2017, Dirk Hartmann.
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

from .base import _SimpleLayoutBase

class Max(_SimpleLayoutBase):
    """Maximized layout

    A simple layout that only displays one window at a time, filling the
    screen. This is suitable for use on laptops and other devices with small
    screens. Conceptually, the windows are managed as a stack, with commands to
    switch to next and previous windows in the stack.
    """

    defaults = [("name", "max", "Name of this layout.")]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Max.defaults)

    def clone(self, group):
        return _SimpleLayoutBase.clone(self, group)

    def add(self, client):
        return self.clients.add(client, 1)

    def configure(self, client, screen):
        if self.clients and client is self.clients.current_client:
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

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next

    cmd_up = cmd_previous
    cmd_down = cmd_next
