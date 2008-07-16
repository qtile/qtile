import copy
import manager

class _Layout:
    commands = None
    def clone(self, group):
        c = copy.copy(self)
        c.group = group
        return c

    def add(self, c):
        """
            Called whenever a client is added to the group, whether the layout
            is current or not. The layout should:
                
                - Configure the window (which may include calling its own
                  configure method on this or maybe all clients).
                - Map it
        """
        pass

    def remove(self, c):
        """
            Called whenever a client is removed from the group, whether the
            layout is current or not. The layout should just de-register the
            client, and then adjust its layout. It need not unmap the window.
        """
        pass

    def configure(self, c):
        """
            Called to configure the dimensions of a client. This method is only
            called when the layout is the current layout.
        """
        raise NotImplementedError


class Max(_Layout):
    name = "max"
    class commands:
        @staticmethod
        def cmd_max_next(q, noskip=False):
            if q.currentLayout.name != self.name:
                raise manager.SkipCommand
            idx = (q.currentGroup.index(q.currentFocus) + 1) % len(q.currentGroup)
            q.currentGroup.focus(q.currentGroup[idx])

        @staticmethod
        def cmd_max_previous(q, noskip=False):
            if q.currentLayout.name != self.name:
                raise manager.SkipCommand
            idx = (q.currentGroup.index(q.currentFocus) - 1) % len(q.currentGroup)
            q.currentGroup.focus(q.currentGroup[idx])

    def configure(self, c):
        if c == self.group.focusClient:
            c.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
        else:
            c.hide()


class Stack(_Layout):
    name = "stack"
    class commands:
        @staticmethod
        def cmd_stack_down(q, noskip=False):
            pass

        @staticmethod
        def cmd_stack_up(q, noskip=False):
            pass

        @staticmethod
        def cmd_stack_swap(q, noskip=False):
            pass

        @staticmethod
        def cmd_stack_move(q, noskip=False):
            pass

    def __init__(self, stacks=2):
        self.stacks = [None]*stacks

    def add(self, c):
        pass

    def remove(self, c):
        pass

    def configure(self, c):
        if c in self.stacks:
            c.place(
                self.group.screen.x,
                self.group.screen.y,
                self.group.screen.width,
                self.group.screen.height,
            )
        else:
            c.hide()
