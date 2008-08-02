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

            It should also set the group focus to the appropriate "next"
            window, as interpreted by the layout.
        """
        pass

    def configure(self, c):
        """
            This method should:
                
                - Configure the dimensions and borders of a window using the
                  .place() method.
                - Call either .hide or .unhide on the window.
        """
        raise NotImplementedError

    def info(self):
        return dict(
            name = self.name,
            group = self.group.name
        )


class StackCommands(command.Commands):
    def cmd_stack_toggle_split(self, q, noskip=False):
        """
            Toggle vertical split on the current layout.
        """
        s = q.currentLayout.currentStack
        if s:
            s.toggleSplit()
        q.currentGroup.layoutAll()

    def cmd_stack_down(self, q, noskip=False):
        """
            Switch to the next window in this stack.
        """
        s = q.currentLayout.currentStack
        if s:
            s.current -= 1
            q.currentGroup.focus(s.cw, False)

    def cmd_stack_up(self, q, noskip=False):
        """
            Switch to the previous window in this stack.
        """
        s = q.currentLayout.currentStack
        if s:
            s.current += 1
            q.currentGroup.focus(s.cw, False)

    def cmd_stack_shuffle_up(self, q, noskip=False):
        """
            Shuffle the order of this stack up.
        """
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleUp(s.lst)
            s.current += 1
        q.currentGroup.layoutAll()

    def cmd_stack_shuffle_down(self, q, noskip=False):
        """
            Shuffle the order of this stack down.
        """
        s = q.currentLayout.currentStack
        if s:
            utils.shuffleDown(s.lst)
            s.current -= 1
        q.currentGroup.layoutAll()

    def cmd_stack_delete(self, q, noskip=False):
        """
            Delete the current stack from the layout.
        """
        q.currentLayout.deleteCurrentStack()

    def cmd_stack_add(self, q, noskip=False):
        """
            Add a stack to the layout.
        """
        q.currentLayout.stacks.append(_WinStack())
        q.currentGroup.layoutAll()

    def cmd_stack_rotate(self, q, noskip=False):
        """
            Rotate order of the stacks.
        """
        utils.shuffleUp(q.currentLayout.stacks)
        q.currentGroup.layoutAll()

    def cmd_stack_next(self, q, noskip=False):
        """
            Focus next stack.
        """
        return q.currentLayout.nextStack()

    def cmd_stack_previous(self, q, noskip=False):
        """
            Focus previous stack.
        """
        return q.currentLayout.previousStack()

    def cmd_stack_current(self, q, noskip=False):
        """
            Return the offset of the current stack.
        """
        return q.currentLayout.currentStackOffset

    def cmd_stack_get(self, q, noskip=False):
        """
            Retrieve the current stacks, returning lists of window names in
            order, starting with the current window of each stack.
        """
        lst = []
        for i in q.currentLayout.stacks:
            s = i[i.current:] + i[:i.current]
            lst.append([i.name for i in s])
        return lst


class _WinStack(object):
    split = False
    _current = 0
    def _getCurrent(self):
        return self._current

    def _setCurrent(self, x):
        if len(self):
            self._current = abs(x%len(self))
        else:
            self._current = 0

    current = property(_getCurrent, _setCurrent)

    @property
    def cw(self):
        return self.lst[self.current]

    def __init__(self):
        self.lst = []

    def toggleSplit(self):
        self.split = False if self.split else True

    def join(self, ws):
        # FIXME: This buggers up window order - windows should be injected BEFORE
        # the current offset.
        self.lst.extend(ws.lst)

    def focus(self, w):
        self.current = self.lst.index(w)

    def add(self, w):
        self.lst.insert(self.current, w)

    def remove(self, w):
        idx = self.lst.index(w)
        self.lst.remove(w)
        if idx > self.current:
            self.current -= 1
        else:
            # This apparently nonsensical assignment caps the value using the
            # property definition.
            self.current = self.current

    def index(self, c):
        return self.lst.index(c)

    def __len__(self):
        return len(self.lst)

    def __getitem__(self, i):
        return self.lst[i]

    def __contains__(self, x):
        return x in self.lst

    def __repr__(self):
        return "_WinStack(%s, %s)"%(self.current, str([i.name for i in self]))

    def info(self):
        return dict(
            windows = [i.name for i in self],
            split = self.split,
            current = self.current,
        )


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
        self.stacks = [_WinStack() for i in range(stacks)]

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
        c.stacks = [_WinStack() for i in self.stacks]
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
            self.stacks[off].join(s)
            if self.stacks[off]:
                self.group.focus(
                    self.stacks[off].cw,
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
            self.group.focus(n.cw, True)

    def previousStack(self):
        if self.currentStackOffset is None:
            return
        n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - self.currentStackOffset - 1
            )
        if n:
            self.group.focus(n.cw, True)

    def focus(self, c):
        for i in self.stacks:
            if c in i:
                i.focus(c)

    def add(self, c):
        if self.group.currentWindow:
            for i in self.stacks:
                if not i:
                    i.add(c)
                    return
            for i in self.stacks:
                if self.group.currentWindow in i:
                    i.add(c)
                    return
        else:
            self.stacks[0].add(c)

    def remove(self, c):
        for i in self.stacks:
            if c in i:
                i.remove(c)
                if len(i) and self.group.layout is self:
                    self.group.focus(i.cw, True)
                return

    def configure(self, c):
        for i, s in enumerate(self.stacks):
            if c in s:
                break
        else:
            c.hide()

        if c is self.group.currentWindow:
            px = self.activePixel
        else:
            px = self.inactivePixel

        columnWidth = int(self.group.screen.dwidth/float(len(self.stacks)))
        xoffset = self.group.screen.dx + i*columnWidth
        winWidth = columnWidth - 2*self.borderWidth

        if s.split:
            columnHeight = int(self.group.screen.dheight/float(len(s)))
            winHeight = columnHeight - 2*self.borderWidth
            yoffset = self.group.screen.dy + s.index(c)*columnHeight
            c.place(
                xoffset,
                yoffset,
                winWidth,
                winHeight,
                self.borderWidth,
                px
            )
            c.unhide()
        else:
            if c == s.cw:
                c.place(
                    xoffset,
                    self.group.screen.dy,
                    winWidth,
                    self.group.screen.dheight - 2*self.borderWidth,
                    self.borderWidth,
                    px
                )
                c.unhide()
            else:
                c.hide()

    def info(self):
        d = _Layout.info(self)
        d["stacks"] = [i.info() for i in self.stacks]
        d["current_stack"] = self.currentStackOffset
        return d
