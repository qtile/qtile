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
from .. import utils


class _WinStack(object):
    split = False
    _current = 0

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, x):
        if len(self):
            self._current = abs(x % len(self))
        else:
            self._current = 0

    @property
    def cw(self):
        if not self.lst:
            return None
        return self.lst[self.current]

    def __init__(self):
        self.lst = []

    def toggleSplit(self):
        self.split = False if self.split else True

    def join(self, ws):
        # FIXME: This buggers up window order -
        # windows should be injected BEFORE
        # the current offset.
        self.lst.extend(ws.lst)

    def focus(self, client):
        self.current = self.lst.index(client)

    def focus_first(self):
        if self.split:
            return self[0]
        else:
            return self.cw

    def focus_next(self, win):
        if self.split:
            idx = self.index(win)
            if idx + 1 < len(self):
                return self[idx + 1]

    def focus_last(self):
        if self.split:
            return self[-1]
        else:
            return self.cw

    def focus_previous(self, win):
        if self.split:
            idx = self.index(win)
            if idx > 0:
                return self[idx - 1]

    def add(self, client):
        self.lst.insert(self.current, client)

    def remove(self, client):
        if client not in self.lst:
            return
        idx = self.lst.index(client)
        self.lst.remove(client)
        if idx > self.current:
            self.current -= 1
        else:
            # This apparently nonsensical assignment caps the value using the
            # property definition.
            self.current = self.current

    def index(self, client):
        return self.lst.index(client)

    def __len__(self):
        return len(self.lst)

    def __getitem__(self, i):
        return self.lst[i]

    def __contains__(self, client):
        return client in self.lst

    def __repr__(self):
        return "_WinStack(%s, %s)" % (
            self.current, str([i.name for i in self])
        )

    def info(self):
        return dict(
            clients=[x.name for x in self],
            split=self.split,
            current=self.current,
        )


class Stack(Layout):
    """
        The stack layout divides the screen horizontally into a set of stacks.
        Commands allow you to switch between stacks, to next and previous
        windows within a stack, and to split a stack to show all windows in the
        stack, or unsplit it to show only the current window. At the moment,
        this is the most mature and flexible layout in Qtile.
    """
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("name", "stack", "Name of this layout."),
        ("autosplit", False, "Auto split all new stacks."),
        ("num_stacks", 2, "Number of stacks."),
        ("fair", False, "Add new windows to the stacks in a round robin way."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Stack.defaults)
        self.stacks = [_WinStack() for i in range(self.num_stacks)]
        for stack in self.stacks:
            if self.autosplit:
                stack.split = True

    @property
    def currentStack(self):
        return self.stacks[self.currentStackOffset]

    @property
    def currentStackOffset(self):
        for i, s in enumerate(self.stacks):
            if self.group.currentWindow in s:
                return i
        return 0

    @property
    def clients(self):
        client_list = []
        for stack in self.stacks:
            client_list.extend(list(stack))
        return client_list

    def clone(self, group):
        c = Layout.clone(self, group)
        # These are mutable
        c.stacks = [_WinStack() for i in self.stacks]
        for stack in c.stacks:
            if self.autosplit:
                stack.split = True
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
            off = self.currentStackOffset or 0
            s = self.stacks[off]
            self.stacks.remove(s)
            off = min(off, len(self.stacks) - 1)
            self.stacks[off].join(s)
            if self.stacks[off]:
                self.group.focus(
                    self.stacks[off].cw,
                    False
                )

    def nextStack(self):
        n = self._findNext(
            self.stacks,
            self.currentStackOffset
        )
        if n:
            self.group.focus(n.cw, True)

    def previousStack(self):
        n = self._findNext(
            list(reversed(self.stacks)),
            len(self.stacks) - self.currentStackOffset - 1
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
            self.currentStack.add(client)

    def remove(self, client):
        currentOffset = self.currentStackOffset
        for i in self.stacks:
            if client in i:
                i.remove(client)
                break
        if self.stacks[currentOffset].cw:
            return self.stacks[currentOffset].cw
        else:
            n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - currentOffset - 1
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

        if client is self.group.currentWindow:
            px = self.group.qtile.colorPixel(self.border_focus)
        else:
            px = self.group.qtile.colorPixel(self.border_normal)

        columnWidth = int(screen.width / float(len(self.stacks)))
        xoffset = screen.x + i * columnWidth
        winWidth = columnWidth - 2 * self.border_width

        if s.split:
            columnHeight = int(screen.height / float(len(s)))
            winHeight = columnHeight - 2 * self.border_width
            yoffset = screen.y + s.index(client) * columnHeight
            client.place(
                xoffset,
                yoffset,
                winWidth,
                winHeight,
                self.border_width,
                px
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
                    px
                )
                client.unhide()
            else:
                client.hide()

    def info(self):
        d = Layout.info(self)
        d["stacks"] = [i.info() for i in self.stacks]
        d["current_stack"] = self.currentStackOffset
        d["clients"] = [c.name for c in self.clients]
        return d

    def cmd_toggle_split(self):
        """
            Toggle vertical split on the current stack.
        """
        self.currentStack.toggleSplit()
        self.group.layoutAll()

    def cmd_down(self):
        """
            Switch to the next window in this stack.
        """
        self.currentStack.current -= 1
        self.group.focus(self.currentStack.cw, False)

    def cmd_up(self):
        """
            Switch to the previous window in this stack.
        """
        self.currentStack.current += 1
        self.group.focus(self.currentStack.cw, False)

    def cmd_shuffle_up(self):
        """
            Shuffle the order of this stack up.
        """
        utils.shuffleUp(self.currentStack.lst)
        self.currentStack.current += 1
        self.group.layoutAll()

    def cmd_shuffle_down(self):
        """
            Shuffle the order of this stack down.
        """
        utils.shuffleDown(self.currentStack.lst)
        self.currentStack.current -= 1
        self.group.layoutAll()

    def cmd_delete(self):
        """
            Delete the current stack from the layout.
        """
        self.deleteCurrentStack()

    def cmd_add(self):
        """
            Add another stack to the layout.
        """
        newstack = _WinStack()
        if self.autosplit:
            newstack.split = True
        self.stacks.append(newstack)
        self.group.layoutAll()

    def cmd_rotate(self):
        """
            Rotate order of the stacks.
        """
        utils.shuffleUp(self.stacks)
        self.group.layoutAll()

    def cmd_next(self):
        """
            Focus next stack.
        """
        return self.nextStack()

    def cmd_previous(self):
        """
            Focus previous stack.
        """
        return self.previousStack()

    def cmd_client_to_next(self):
        """
            Send the current client to the next stack.
        """
        return self.cmd_client_to_stack(self.currentStackOffset + 1)

    def cmd_client_to_previous(self):
        """
            Send the current client to the previous stack.
        """
        return self.cmd_client_to_stack(self.currentStackOffset - 1)

    def cmd_client_to_stack(self, n):
        """
            Send the current client to stack n, where n is an integer offset.
            If is too large or less than 0, it is wrapped modulo the number of
            stacks.
        """
        if not self.currentStack:
            return
        next = n % len(self.stacks)
        win = self.currentStack.cw
        self.currentStack.remove(win)
        self.stacks[next].add(win)
        self.stacks[next].focus(win)
        self.group.layoutAll()

    def cmd_info(self):
        return self.info()
