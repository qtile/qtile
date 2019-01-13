# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Thomas Sarboni
# Copyright (c) 2014-2015 Tycho Andersen
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

from .. import hook, bar, layout
from . import base


class DebugInfo(base._TextBox):
    """Displays debugging infos about selected window"""
    orientations = base.ORIENTATION_HORIZONTAL

    def __init__(self, **config):
        base._TextBox.__init__(self, text=" ", width=bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.layout_change(self.update)
        hook.subscribe.float_change(self.update)

    def update(self, *args):
        old_layout_width = self.layout.width

        w = self.bar.screen.group.current_window

        if isinstance(w.group.layout, layout.Stack):
            stack = w.group.layout.current_stack
            stack_offset = w.group.layout.current_stack_offset
            index = stack.lst.index(w)
            current = stack.current
            self.text = ("Stack: %s Index: %s Current: %s"
                         % (stack_offset, index, current))
        elif isinstance(w.group.layout, layout.TreeTab):
            node = w.group.layout._nodes[w]
            node_index = node.parent.children.index(node)
            snode = node
            level = 1
            while not isinstance(snode, layout.tree.Section):
                snode = snode.parent
                level += 1
            section_index = snode.parent.children.index(snode)
            self.text = ("Level: %s SectionIndex: %s NodeIndex: %s"
                         % (level, section_index, node_index))

        if self.layout.width != old_layout_width:
            self.bar.draw()
        else:
            self.draw()
