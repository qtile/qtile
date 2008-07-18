import copy
import manager, utils

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


class Max(_Layout):
    name = "max"
    class commands:
        @staticmethod
        def cmd_max_next(q, noskip=False):
            if q.currentLayout.name != "max":
                raise manager.SkipCommand
            idx = (q.currentGroup.index(q.currentClient) + 1) % len(q.currentGroup)
            q.currentGroup.focus(q.currentGroup[idx])

        @staticmethod
        def cmd_max_previous(q, noskip=False):
            if q.currentLayout.name != "max":
                raise manager.SkipCommand
            idx = (q.currentGroup.index(q.currentClient) - 1) % len(q.currentGroup)
            q.currentGroup.focus(q.currentGroup[idx])

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


class Stack(_Layout):
    name = "stack"
    class commands:
        @staticmethod
        def cmd_stack_down(q, noskip=False):
            s = q.currentLayout.currentStack
            if s:
                utils.shuffleDown(s)
                q.currentGroup.layoutAll()

        @staticmethod
        def cmd_stack_up(q, noskip=False):
            s = q.currentLayout.currentStack
            if s:
                utils.shuffleUp(s)
                q.currentGroup.layoutAll()

        @staticmethod
        def cmd_stack_delete(q, noskip=False):
            if len(q.currentLayout.stacks) > 1:
                off = q.currentLayout.currentStackOffset or 0
                s = q.currentLayout.stacks[off]
                q.currentLayout.stacks.remove(s)
                off = min(off, len(q.currentLayout.stacks)-1)
                q.currentLayout.stacks[off].extend(s)
                if q.currentLayout.stacks[off]:
                    q.currentGroup.focus(
                        q.currentLayout.stacks[off][0]
                    )

        @staticmethod
        def cmd_stack_add(q, noskip=False):
            q.currentLayout.stacks.append([])
            q.currentGroup.layoutAll()

        @staticmethod
        def cmd_stack_rotate(q, noskip=False):
            utils.shuffleUp(q.currentLayout.stacks)

        @staticmethod
        def cmd_stack_next(q, noskip=False):
            l = q.currentLayout
            for i in l.stacks[l.currentStackOffset:]:
                if i:
                    break
            else:
                for i in l.stacks[:l.currentStackOffset]:
                    if i:
                        break
            if i:
                q.currentGroup.focus(i[0])

        @staticmethod
        def cmd_stack_previous(q, noskip=False):
            pass

        @staticmethod
        def cmd_stack_current(q, noskip=False):
            return q.currentLayout.currentStackOffset

        @staticmethod
        def cmd_stack_get(q, noskip=False):
            if q.currentLayout.name != "stack":
                raise manager.SkipCommand
            lst = []
            for i in q.currentLayout.stacks:
                s = []
                for j in i:
                    s.append(j.name)
                lst.append(s)
            return lst

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
