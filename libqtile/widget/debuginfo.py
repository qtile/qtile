from .. import hook, bar, layout
from . import base
import logging

class DebugInfo(base._TextBox):
    """
        Displays debugging infos about selected window
    """
    def __init__(self, **config):
        self.log = logging.getLogger('qtile')
        base._TextBox.__init__(self, " ", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.layout_change(self.update)
        hook.subscribe.float_change(self.update)

    def update(self, *args):
        old_layout_width = self.layout.width

        w = self.bar.screen.group.currentWindow

        if isinstance(w.group.layout, layout.Stack):
            stack = w.group.layout.currentStack
            stackOffset = w.group.layout.currentStackOffset
            idx = stack.lst.index(w)
            current = stack.current
            self.text = "Stack: %s Idx: %s Cur: %s" % (stackOffset,
                                                       idx,
                                                       current)
        elif isinstance(w.group.layout, layout.TreeTab):
            node = w.group.layout._nodes[w]
            nodeIdx = node.parent.children.index(node)
            snode = node
            level = 1
            while not isinstance(snode, layout.tree.Section):
                snode = snode.parent
                level += 1
            sectionIdx = snode.parent.children.index(snode)
            self.text = "Level: %s SectionIdx: %s NodeIdx: %s" % (level,
                                                                  sectionIdx,
                                                                  nodeIdx)

        if self.layout.width != old_layout_width:
            self.bar.draw()
        else:
            self.draw()
