import copy
import manager, utils, command

class _Layout:
    commands = None
    def clone(self, group):
        c = copy.copy(self)
        c.group = group
        return c

    def focus(self, c):
        """
            Called whenever the focus changes.
        """
        pass

    def add(self, c):
        """
            Called whenever a client is added to the group, whether the layout
            is current or not. The layout should just add the window to its
            internal datastructures, without mapping or configuring.
        """
        pass

    def remove(self, c):
        """
            Called whenever a client is removed from the group, whether the
            layout is current or not. The layout should just de-register the
            client from its data structures, without unmapping the window.
        """
        pass

    def configure(self, c):
        """
            This method should:
                
                - Configure the dimensions of a client.
                - Call either .hide or .unhide on the client.
        """
        raise NotImplementedError


class MaxCommands(command.Commands):
    def cmd_max_next(self, q, noskip=False):
        if q.currentLayout.name != "max":
            raise manager.SkipCommand
        idx = (q.currentGroup.index(q.currentClient) + 1) % len(q.currentGroup)
        q.currentGroup.focus(q.currentGroup[idx])

    def cmd_max_previous(self, q, noskip=False):
        if q.currentLayout.name != "max":
            raise manager.SkipCommand
        idx = (q.currentGroup.index(q.currentClient) - 1) % len(q.currentGroup)
        q.currentGroup.focus(q.currentGroup[idx])


class Max(_Layout):
    name = "max"
    commands = MaxCommands()
    def configure(self, c):
        if c == self.group.currentClient:
            c.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
            c.unhide()
        else:
            c.hide()


class StackCommands(command.Commands):
    def cmd_stack_down(self, q, noskip=False):
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleDown(s)
            q.currentGroup.layoutAll()

    def cmd_stack_up(self, q, noskip=False):
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleUp(s)
            q.currentGroup.layoutAll()

    def cmd_stack_delete(self, q, noskip=False):
        q.currentLayout.deleteCurrentStack()

    def cmd_stack_add(self, q, noskip=False):
        q.currentLayout.stacks.append([])
        q.currentGroup.layoutAll()

    def cmd_stack_rotate(self, q, noskip=False):
        utils.shuffleUp(q.currentLayout.stacks)

    def cmd_stack_next(self, q, noskip=False):
        return q.currentLayout.nextStack()

    def cmd_stack_previous(self, q, noskip=False):
        return q.currentLayout.previousStack()

    def cmd_stack_current(self, q, noskip=False):
        return q.currentLayout.currentStackOffset

    def cmd_stack_get(self, q, noskip=False):
        if q.currentLayout.name != "stack":
            raise manager.SkipCommand
        lst = []
        for i in q.currentLayout.stacks:
            s = []
            for j in i:
                s.append(j.name)
            lst.append(s)
        return lst


class Stack(_Layout):
    name = "stack"
    commands = StackCommands()
    def __init__(self, stacks=2):
        self.stacks = [[] for i in range(stacks)]

    @property
    def currentStack(self):
        return self.stacks[self.currentStackOffset]

    @property
    def currentStackOffset(self):
        for i, s in enumerate(self.stacks):
            if self.group.currentClient in s:
                return i

    def _findNext(self, lst, offset):
        for i in lst[offset+1:]:
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
            off = min(off, len(self.stacks)-1)
            self.stacks[off].extend(s)
            if self.stacks[off]:
                self.group.focus(
                    self.stacks[off][0]
                )

    def nextStack(self):
        if self.currentStackOffset is None:
            return
        n = self._findNext(
                self.stacks,
                self.currentStackOffset
            )
        if n:
            self.group.focus(n[0])

    def previousStack(self):
        if self.currentStackOffset is None:
            return
        n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - self.currentStackOffset - 1
            )
        if n:
            self.group.focus(n[0])

    def focus(self, c):
        for i in self.stacks:
            if c in i:
                i.remove(c)
                i.insert(0, c)

    def add(self, c):
        if self.group.currentClient:
            for i in self.stacks:
                if not i:
                    i.append(c)
                    return
            for i in self.stacks:
                if self.group.currentClient in i:
                    idx = i.index(self.group.currentClient)
                    i.insert(idx, c)
                    return
        else:
            self.stacks[0].insert(0, c)

    def remove(self, c):
        for i in self.stacks:
            if c in i:
                i.remove(c)
                return

    def configure(self, c):
        column = int(self.group.screen.width/float(len(self.stacks)))
        for i, s in enumerate(self.stacks):
            if s and c == s[0]:
                xoffset = i * column
                c.place(
                    xoffset,
                    self.group.screen.y,
                    column,
                    self.group.screen.height,
                )
                c.unhide()
                return
        else:
            c.hide()
