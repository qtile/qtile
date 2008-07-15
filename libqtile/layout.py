import copy

class _Layout:
    commands = None
    def clone(self, group):
        c = copy.copy(self)
        c.group = group
        return c


class Max(_Layout):
    name = "max"
    class commands:
        @staticmethod
        def cmd_max_next(qtile, noskip=False):
            idx = (qtile.group.clients.index(qtile.group.focusClient) + 1) % len(qtile.group.clients)
            qtile.group.focus(qtile.group.clients[idx])

        @staticmethod
        def cmd_max_previous(qtile, noskip=False):
            idx = (qtile.group.clients.index(qtile.group.focusClient) - 1) % len(qtile.group.clients)
            qtile.group.focus(qtile.group.clients[idx])

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
    def __init__(self, columns=2):
        self.columns = columns

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

    def cmd_stack_down(self, qtile, noskip=False):
        pass

    def cmd_stack_up(self, qtile, noskip=False):
        pass

    def cmd_stack_swap(self, qtile, noskip=False):
        pass

    def cmd_stack_move(self, qtile, noskip=False):
        pass
