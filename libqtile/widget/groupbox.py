from .. import bar, hook
import base

class GroupBox(base._Widget):
    BOXPADDING_SIDE = 8
    PADDING = 3
    BORDERWIDTH = 1
    def click(self, x, y):
        groupOffset = x/self.boxwidth
        if len(self.qtile.groups) - 1 >= groupOffset:
            self.bar.screen.setGroup(self.qtile.groups[groupOffset])

    def _configure(self, qtile, bar, theme):
        base._Widget._configure(self, qtile, bar, theme)
        # Placeholder
        self.width = 100
        hook.subscribe("setgroup", self.draw)
        hook.subscribe("window_add", self.draw)
        self.setup_hooks()

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        return

    def setup_hooks(self):
        draw = self.draw
        def hook_response(*args, **kwargs):
            self.draw()
        hook.subscribe("client_new", hook_response)
        hook.subscribe("client_urgent_hint_changed", hook_response)
        hook.subscribe("client_killed", hook_response)

