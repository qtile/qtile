import copy, sys
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
        """
        pass

    def configure(self, c):
        """
            This method should:
                
                - Configure the dimensions of a window.
                - Call either .hide or .unhide on the window.
        """
        raise NotImplementedError

    def info(self):
        return dict(
            name = self.name,
            group = self.group.name
        )


class MaxCommands(command.Commands):
    def cmd_max_next(self, q, noskip=False):
        if not q.currentWindow:
            return
        idx = (q.currentGroup.index(q.currentWindow) + 1) % len(q.currentGroup)
        q.currentGroup.focus(q.currentGroup[idx], False)

    def cmd_max_previous(self, q, noskip=False):
        if not q.currentWindow:
            return
        idx = (q.currentGroup.index(q.currentWindow) - 1) % len(q.currentGroup)
        q.currentGroup.focus(q.currentGroup[idx], False)


class Max(_Layout):
    name = "max"
    commands = MaxCommands()
    def configure(self, c):
        if c == self.group.currentWindow:
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


class StackCommands(command.Commands):
    def cmd_stack_down(self, q, noskip=False):
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleDown(s)
            q.currentGroup.focus(s[0], False)

    def cmd_stack_up(self, q, noskip=False):
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleUp(s)
            q.currentGroup.focus(s[0], False)

    def cmd_stack_delete(self, q, noskip=False):
        q.currentLayout.deleteCurrentStack()

    def cmd_stack_add(self, q, noskip=False):
        q.currentLayout.stacks.append([])
        q.currentGroup.layoutAll()

    def cmd_stack_rotate(self, q, noskip=False):
        utils.shuffleUp(q.currentLayout.stacks)
        q.currentGroup.layoutAll()

    def cmd_stack_next(self, q, noskip=False):
        return q.currentLayout.nextStack()

    def cmd_stack_previous(self, q, noskip=False):
        return q.currentLayout.previousStack()

    def cmd_stack_current(self, q, noskip=False):
        return q.currentLayout.currentStackOffset

    def cmd_stack_get(self, q, noskip=False):
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
    def __init__(self, stacks=2, borderWidth=1, active="#00009A", inactive="black"):
        """
            stacks: Number of stacks to start with.
            borderWidth: Width of window borders.
            active: Color of the active window border.
            inactive: Color of the inactive window border.
        """
        self.borderWidth, self.active, self.inactive = borderWidth, active, inactive
        self.activePixel, self.inactivePixel = None, None
        self.stacks = [[] for i in range(stacks)]

    @property
    def currentStack(self):
        return self.stacks[self.currentStackOffset]

    @property
    def currentStackOffset(self):
        for i, s in enumerate(self.stacks):
            if self.group.currentWindow in s:
                return i

    def clone(self, group):
        if not self.activePixel:
            colormap = group.qtile.display.screen().default_colormap
            self.activePixel = colormap.alloc_named_color(self.active).pixel
            self.inactivePixel = colormap.alloc_named_color(self.inactive).pixel
        c = _Layout.clone(self, group)
        # These are mutable
        c.stacks = [[] for i in self.stacks]
        return c

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
                    self.stacks[off][0],
                    False
                )

    def nextStack(self):
        if self.currentStackOffset is None:
            return
        n = self._findNext(
                self.stacks,
                self.currentStackOffset
            )
        if n:
            self.group.focus(n[0], True)

    def previousStack(self):
        if self.currentStackOffset is None:
            return
        n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - self.currentStackOffset - 1
            )
        if n:
            self.group.focus(n[0], True)

    def focus(self, c):
        for i in self.stacks:
            if c in i:
                i.remove(c)
                i.insert(0, c)

    def add(self, c):
        if self.group.currentWindow:
            for i in self.stacks:
                if not i:
                    i.append(c)
                    return
            for i in self.stacks:
                if self.group.currentWindow in i:
                    idx = i.index(self.group.currentWindow)
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
        column = int(self.group.screen.dwidth/float(len(self.stacks)))
        for i, s in enumerate(self.stacks):
            if s and c == s[0]:
                xoffset = self.group.screen.dx + i*column
                if i == self.currentStackOffset:
                    px = self.activePixel
                else:
                    px = self.inactivePixel
                c.place(
                    xoffset,
                    self.group.screen.dy,
                    column - 2*self.borderWidth,
                    self.group.screen.dheight - 2*self.borderWidth,
                    self.borderWidth,
                    px
                )
                c.unhide()
                return
        else:
            c.hide()

    def info(self):
        d = _Layout.info(self)
        lst = []
        for i in self.stacks:
            lst.append([j.name for j in i])
        d["stacks"] = lst
        d["current_stack"] = self.currentStackOffset
        return d
