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

from __future__ import division

from .base import Layout, _ClientList
from .. import utils


class _WinStack(_ClientList):

    # shortcuts for current client and index used in Columns layout
    cw = _ClientList.current_client

    def __init__(self, autosplit=False):
        _ClientList.__init__(self)
        self.split = autosplit

    def toggleSplit(self):
        self.split = False if self.split else True

    def __str__(self):
        return "_WinStack: %s, %s" % (
            self.current, str([client.name for client in self.clients])
        )

    def info(self):
        info = _ClientList.info(self)
        info['split'] = self.split
        return info


class Stack(Layout):
    """A layout composed of stacks of windows

    The stack layout divides the screen horizontally into a set of stacks.
    Commands allow you to switch between stacks, to next and previous windows
    within a stack, and to split a stack to show all windows in the stack, or
    unsplit it to show only the current window.

    Unlike the columns layout the number of stacks is fixed.
    """
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_width", 1, "Border width."),
        ("name", "stack", "Name of this layout."),
        ("autosplit", False, "Auto split all new stacks."),
        ("num_stacks", 2, "Number of stacks."),
        ("fair", False, "Add new windows to the stacks in a round robin way."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Stack.defaults)
        self.stacks = [_WinStack(autosplit=self.autosplit)
                       for i in range(self.num_stacks)]

    @property
    def current_stack(self):
        return self.stacks[self.current_stack_offset]

    @property
    def current_stack_offset(self):
        for i, s in enumerate(self.stacks):
            if self.group.currentWindow in s:
                return i
        return 0

    @property
    def clients(self):
        client_list = []
        for stack in self.stacks:
            client_list.extend(stack.clients)
        return client_list

    def clone(self, group):
        c = Layout.clone(self, group)
        # These are mutable
        c.stacks = [_WinStack(autosplit=self.autosplit) for i in self.stacks]
        return c

    def _findNext(self, lst, offset):
        for i in lst[offset + 1:]:
            if i:
                return i
        else:
            for i in lst[:offset]:
                if i:
                    return i

    def deleteCurrentStack(self):
        if len(self.stacks) > 1:
            off = self.current_stack_offset or 0
            s = self.stacks[off]
            self.stacks.remove(s)
            off = min(off, len(self.stacks) - 1)
            self.stacks[off].join(s, 1)
            if self.stacks[off]:
                self.group.focus(
                    self.stacks[off].cw,
                    False
                )

    def nextStack(self):
        n = self._findNext(
            self.stacks,
            self.current_stack_offset
        )
        if n:
            self.group.focus(n.cw, True)

    def previousStack(self):
        n = self._findNext(
            list(reversed(self.stacks)),
            len(self.stacks) - self.current_stack_offset - 1
        )
        if n:
            self.group.focus(n.cw, True)

    def focus(self, client):
        for i in self.stacks:
            if client in i:
                i.focus(client)

    def focus_first(self):
        for i in self.stacks:
            if i:
                return i.focus_first()

    def focus_last(self):
        for i in reversed(self.stacks):
            if i:
                return i.focus_last()

    def focus_next(self, client):
        iterator = iter(self.stacks)
        for i in iterator:
            if client in i:
                next = i.focus_next(client)
                if next:
                    return next
                break
        else:
            return

        for i in iterator:
            if i:
                return i.focus_first()

    def focus_previous(self, client):
        iterator = iter(reversed(self.stacks))
        for i in iterator:
            if client in i:
                next = i.focus_previous(client)
                if next:
                    return next
                break
        else:
            return

        for i in iterator:
            if i:
                return i.focus_last()

    def add(self, client):
        for i in self.stacks:
            if not i:
                i.add(client)
                return
        if self.fair:
            target = min(self.stacks, key=len)
            target.add(client)
        else:
            self.current_stack.add(client)

    def remove(self, client):
        current_offset = self.current_stack_offset
        for i in self.stacks:
            if client in i:
                i.remove(client)
                break
        if self.stacks[current_offset].cw:
            return self.stacks[current_offset].cw
        else:
            n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - current_offset - 1
            )
            if n:
                return n.cw

    def configure(self, client, screen):
        for i, s in enumerate(self.stacks):
            if client in s:
                break
        else:
            client.hide()
            return

        if client.has_focus:
            px = self.group.qtile.color_pixel(self.border_focus)
        else:
            px = self.group.qtile.color_pixel(self.border_normal)

        column_width = int(screen.width / len(self.stacks))
        xoffset = screen.x + i * column_width
        winWidth = column_width - 2 * self.border_width

        if s.split:
            column_height = int(screen.height / len(s))
            winHeight = column_height - 2 * self.border_width
            yoffset = screen.y + s.index(client) * column_height
            client.place(
                xoffset,
                yoffset,
                winWidth,
                winHeight,
                self.border_width,
                px,
                margin=self.margin,
            )
            client.unhide()
        else:
            if client == s.cw:
                client.place(
                    xoffset,
                    screen.y,
                    winWidth,
                    screen.height - 2 * self.border_width,
                    self.border_width,
                    px,
                    margin=self.margin,
                )
                client.unhide()
            else:
                client.hide()

    def info(self):
        d = Layout.info(self)
        d["stacks"] = [i.info() for i in self.stacks]
        d["current_stack"] = self.current_stack_offset
        d["clients"] = [c.name for c in self.clients]
        return d

    def cmd_toggle_split(self):
        """Toggle vertical split on the current stack"""
        self.current_stack.toggleSplit()
        self.group.layoutAll()

    def cmd_down(self):
        """Switch to the next window in this stack"""
        self.current_stack.current_index -= 1
        self.group.focus(self.current_stack.cw, False)

    def cmd_up(self):
        """Switch to the previous window in this stack"""
        self.current_stack.current_index += 1
        self.group.focus(self.current_stack.cw, False)

    def cmd_shuffle_up(self):
        """Shuffle the order of this stack up"""
        self.current_stack.rotate_up()
        self.group.layoutAll()

    def cmd_shuffle_down(self):
        """Shuffle the order of this stack down"""
        self.current_stack.rotate_down()
        self.group.layoutAll()

    def cmd_delete(self):
        """Delete the current stack from the layout"""
        self.deleteCurrentStack()

    def cmd_add(self):
        """Add another stack to the layout"""
        newstack = _WinStack(autosplit=self.autosplit)
        if self.autosplit:
            newstack.split = True
        self.stacks.append(newstack)
        self.group.layoutAll()

    def cmd_rotate(self):
        """Rotate order of the stacks"""
        utils.shuffleUp(self.stacks)
        self.group.layoutAll()

    def cmd_next(self):
        """Focus next stack"""
        return self.nextStack()

    def cmd_previous(self):
        """Focus previous stack"""
        return self.previousStack()

    def cmd_client_to_next(self):
        """Send the current client to the next stack"""
        return self.cmd_client_to_stack(self.current_stack_offset + 1)

    def cmd_client_to_previous(self):
        """Send the current client to the previous stack"""
        return self.cmd_client_to_stack(self.current_stack_offset - 1)

    def cmd_client_to_stack(self, n):
        """
        Send the current client to stack n, where n is an integer offset.  If
        is too large or less than 0, it is wrapped modulo the number of stacks.
        """
        if not self.current_stack:
            return
        next = n % len(self.stacks)
        win = self.current_stack.cw
        self.current_stack.remove(win)
        self.stacks[next].add(win)
        self.stacks[next].focus(win)
        self.group.layoutAll()

    def cmd_info(self):
        return self.info()
