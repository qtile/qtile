# -*- coding:utf-8 -*-
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2012 roger
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Arnas Udovicius
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Nathan Hoad
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Thomas Sarboni
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

from libqtile import drawer, hook
from libqtile.backend.x11 import window
from libqtile.layout.base import Layout

to_superscript = dict(zip(map(ord, u'0123456789'), map(ord, u'⁰¹²³⁴⁵⁶⁷⁸⁹')))


class TreeNode:
    def __init__(self):
        self.children = []
        self.parent = None
        self.expanded = True
        self._children_top = None
        self._children_bot = None

    def add(self, node, hint=None):
        """Add a node below this node

        The `hint` is a node to place the new node after in this nodes
        children.
        """
        node.parent = self
        if hint is not None:
            try:
                idx = self.children.index(hint)
            except ValueError:
                pass
            else:
                self.children.insert(idx + 1, node)
                return
        self.children.append(node)

    def draw(self, layout, top, level=0):
        """Draw the node and its children to a layout

        Draws this node to the given layout (presumably a TreeTab), starting
        from a y-offset of `top` and at the given level.
        """
        self._children_top = top
        if self.expanded:
            for i in self.children:
                top = i.draw(layout, top, level)
        self._children_bot = top
        return top

    def button_press(self, x, y):
        """Returns self or sibling which got the click"""
        # if we store the locations of each child, it would be possible to do
        # this without having to traverse the tree...
        if not (self._children_top <= y < self._children_bot):
            return
        for i in self.children:
            res = i.button_press(x, y)
            if res is not None:
                return res

    def add_superscript(self, title):
        """Prepend superscript denoting the number of hidden children"""
        if not self.expanded and self.children:
            return "{:d}".format(
                len(self.children)
            ).translate(to_superscript) + title
        return title

    def get_first_window(self):
        """Find the first Window under this node

        Returns self if this is a `Window`, otherwise finds first `Window` by
        depth-first search
        """
        if isinstance(self, Window):
            return self
        if self.expanded:
            for i in self.children:
                node = i.get_first_window()
                if node:
                    return node

    def get_last_window(self):
        """Find the last Window under this node

        Finds last `Window` by depth-first search, otherwise returns self if
        this is a `Window`.
        """
        if self.expanded:
            for i in reversed(self.children):
                node = i.get_last_window()
                if node:
                    return node
        if isinstance(self, Window):
            return self

    def get_next_window(self):
        if self.children and self.expanded:
            return self.children[0]
        node = self
        while not isinstance(node, Root):
            parent = node.parent
            idx = parent.children.index(node)
            for i in range(idx + 1, len(parent.children)):
                res = parent.children[i].get_first_window()
                if res:
                    return res
            node = parent

    def get_prev_window(self):
        node = self
        while not isinstance(node, Root):
            parent = node.parent
            idx = parent.children.index(node)
            if idx == 0 and isinstance(parent, Window):
                return parent
            for i in range(idx - 1, -1, -1):
                res = parent.children[i].get_last_window()
                if res:
                    return res
            node = parent


class Root(TreeNode):
    def __init__(self, sections, default_section=None):
        super().__init__()
        self.sections = {}
        for section in sections:
            self.add_section(section)
        if default_section is None:
            self.def_section = self.children[0]
        else:
            self.def_section = self.sections[default_section]

    def add(self, win, hint=None):
        """Add a new window

        Adds a new `Window` to the tree.  The location of the new node is
        controlled by looking:

            * `hint` kwarg - place the node next to this node
            * win.tree_section - place the window in the given section, by name
            * default section - fallback to default section (first section, if
              not otherwise set)
        """
        parent = None

        if hint is not None:
            parent = hint.parent

        if parent is None:
            sect = getattr(win, 'tree_section', None)
            if sect is not None:
                parent = self.sections.get(sect)

        if parent is None:
            parent = self.def_section

        node = Window(win)
        parent.add(node, hint=hint)
        return node

    def add_section(self, name):
        """Add a new Section with the given name"""
        if name in self.sections:
            raise ValueError("Duplicate section name")
        node = Section(name)
        node.parent = self
        self.sections[name] = node
        self.children.append(node)

    def del_section(self, name):
        """Remove the Section with the given name"""
        if name not in self.sections:
            raise ValueError("Section name not found")
        if len(self.children) == 1:
            raise ValueError("Can't delete last section")

        sec = self.sections[name]
        # move the children of the deleted section to the previous section
        # if delecting the first section, add children to second section
        idx = min(self.children.index(sec), 1)
        next_sec = self.children[idx - 1]
        # delete old section, reparent children to next section
        del self.children[idx]
        next_sec.children.extend(sec.children)
        for i in sec.children:
            i.parent = next_sec


class Section(TreeNode):
    def __init__(self, title):
        super().__init__()
        self.title = title

    def draw(self, layout, top, level=0):
        del layout._layout.width  # no centering
        # draw a horizontal line above the section
        layout._drawer.draw_hbar(
            layout.section_fg,
            0,
            layout.panel_width,
            top,
            linewidth=1
        )
        # draw the section title
        layout._layout.font_size = layout.section_fontsize
        layout._layout.text = self.add_superscript(self.title)
        layout._layout.colour = layout.section_fg
        layout._layout.draw(
            x=layout.section_left,
            y=top + layout.section_top
        )
        top += layout._layout.height + \
            layout.section_top + \
            layout.section_padding

        # run the TreeNode draw to draw children (if expanded)
        top = super().draw(layout, top, level)

        return top + layout.section_bottom


class Window(TreeNode):
    def __init__(self, win):
        super().__init__()
        self.window = win
        self._title_top = None

    def draw(self, layout, top, level=0):
        self._title_top = top

        # setup parameters for drawing self
        left = layout.padding_left + level * layout.level_shift
        layout._layout.font_size = layout.fontsize
        layout._layout.text = self.add_superscript(self.window.name)
        if self.window is layout._focused:
            fg = layout.active_fg
            bg = layout.active_bg
        elif self.window.urgent:
            fg = layout.urgent_fg
            bg = layout.urgent_bg
        else:
            fg = layout.inactive_fg
            bg = layout.inactive_bg
        layout._layout.colour = fg
        layout._layout.width = layout.panel_width - left
        # get a text frame from the above
        framed = layout._layout.framed(
            layout.border_width,
            bg,
            layout.padding_x,
            layout.padding_y
        )
        # draw the text frame at the given point
        framed.draw_fill(left, top)

        top += framed.height + layout.vspace + layout.border_width

        # run the TreeNode draw to draw children (if expanded)
        return super().draw(layout, top, level + 1)

    def button_press(self, x, y):
        """Returns self if clicked on title else returns sibling"""
        if self._title_top <= y < self._children_top:
            return self
        return super().button_press(x, y)

    def remove(self):
        """Removes this Window

        If this window has children, the first child takes the place of this
        window, and any remaining children are reparented to that node
        """
        if self.children:
            head = self.children[0]
            # add the first child to our parent, next to ourselves
            self.parent.add(head, hint=self)
            # move remaining children to be under the new head
            for i in self.children[1:]:
                head.add(i)

        self.parent.children.remove(self)
        del self.children


class TreeTab(Layout):
    """Tree Tab Layout

    This layout works just like Max but displays tree of the windows at the
    left border of the screen_rect, which allows you to overview all opened windows.
    It's designed to work with ``uzbl-browser`` but works with other windows
    too.

    The panel at the left border contains sections, each of which contains
    windows. Initially the panel looks like flat lists inside its
    section, and looks like trees if some of the windows are "moved" left or
    right.

    For example, it looks like below with two sections initially:

    ::

        +------------+
        |Section Foo |
        +------------+
        | Window A   |
        +------------+
        | Window B   |
        +------------+
        | Window C   |
        +------------+
        |Section Bar |
        +------------+

    And then it will look like below if "Window B" is moved right and "Window C"
    is moved right too:

    ::

        +------------+
        |Section Foo |
        +------------+
        | Window A   |
        +------------+
        |  Window B  |
        +------------+
        |   Window C |
        +------------+
        |Section Bar |
        +------------+
    """

    defaults = [
        ("bg_color", "000000", "Background color of tabs"),
        ("active_bg", "000080", "Background color of active tab"),
        ("active_fg", "ffffff", "Foreground color of active tab"),
        ("urgent_bg", "ff0000", "Background color of urgent tab"),
        ("urgent_fg", "ffffff", "Foreground color of urgent tab"),
        ("inactive_bg", "606060", "Background color of inactive tab"),
        ("inactive_fg", "ffffff", "Foreground color of inactive tab"),
        ("margin_left", 6, "Left margin of tab panel"),
        ("margin_y", 6, "Vertical margin of tab panel"),
        ("padding_left", 6, "Left padding for tabs"),
        ("padding_x", 6, "Left padding for tab label"),
        ("padding_y", 2, "Top padding for tab label"),
        ("border_width", 2, "Width of the border"),
        ("vspace", 2, "Space between tabs"),
        ("level_shift", 8, "Shift for children tabs"),
        ("font", "sans", "Font"),
        ("fontsize", 14, "Font pixel size."),
        ("fontshadow", None, "font shadow color, default is None (no shadow)"),
        ("section_fontsize", 11, "Font pixel size of section label"),
        ("section_fg", "ffffff", "Color of section label"),
        ("section_top", 4, "Top margin of section label"),
        ("section_bottom", 6, "Bottom margin of section"),
        ("section_padding", 4, "Bottom of margin section label"),
        ("section_left", 4, "Left margin of section label"),
        ("panel_width", 150, "Width of the left panel"),
        ("sections", ['Default'], "Foreground color of inactive tab"),
        ("previous_on_rm", False, "Focus previous window on close instead of first."),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(TreeTab.defaults)
        self._focused = None
        self._panel = None
        self._drawer = None
        self._layout = None
        self._tree = Root(self.sections)
        self._nodes = {}

    def clone(self, group):
        c = Layout.clone(self, group)
        c._focused = None
        c._panel = None
        c._tree = Root(self.sections)
        return c

    def focus(self, win):
        self._focused = win

    def focus_first(self):
        win = self._tree.get_first_window()
        if win:
            return win.window

    def focus_last(self):
        win = self._tree.get_last_window()
        if win:
            return win.window

    def focus_next(self, client):
        win = self._nodes[client].get_next_window()
        if win:
            return win.window

    def focus_previous(self, client):
        win = self._nodes[client].get_prev_window()
        if win:
            return win.window

    def blur(self):
        # Does not clear current window, will change if new one
        # will be focused. This works better when floating window
        # will be next focused one
        pass

    def add(self, win):
        if self._focused:
            node = self._tree.add(win, hint=self._nodes[self._focused])
        else:
            node = self._tree.add(win)
        self._nodes[win] = node

    def remove(self, win):
        if win not in self._nodes:
            return

        if self.previous_on_rm:
            self._focused = self.focus_previous(win)
        else:
            self._focused = self.focus_first()

        if self._focused is win:
            self._focused = None

        self._nodes[win].remove()
        del self._nodes[win]
        self.draw_panel()

    def _create_panel(self, screen_rect):
        self._panel = window.Internal.create(
            self.group.qtile,
            screen_rect.x,
            screen_rect.y,
            self.panel_width,
            100
        )
        self._create_drawer(screen_rect)
        self._panel.handle_Expose = self._handle_Expose
        self._panel.handle_ButtonPress = self._handle_ButtonPress
        self.group.qtile.windows_map[self._panel.wid] = self._panel
        hook.subscribe.client_name_updated(self.draw_panel)
        hook.subscribe.focus_change(self.draw_panel)

    def _handle_Expose(self, e):  # noqa: N802
        self.draw_panel()

    def draw_panel(self, *args):
        if not self._panel:
            return
        self._drawer.clear(self.bg_color)
        self._tree.draw(self, 0)
        self._drawer.draw(offsetx=0, width=self.panel_width)

    def _handle_ButtonPress(self, event):  # noqa: N802
        node = self._tree.button_press(event.event_x, event.event_y)
        if node:
            self.group.focus(node.window, False)

    def configure(self, client, screen_rect):
        if self._nodes and client is self._focused:
            client.place(
                screen_rect.x, screen_rect.y,
                screen_rect.width, screen_rect.height,
                0,
                None
            )
            client.unhide()
        else:
            client.hide()

    def finalize(self):
        Layout.finalize(self)
        if self._drawer is not None:
            self._drawer.finalize()

    def info(self):

        def show_section_tree(root):
            '''Show a section tree in a nested list, whose every element has the form: `[root, [subtrees]]`.

            For `[root, [subtrees]]`, The first element is the root node, and the second is its a list of its subtrees.
            For example, a section with below windows hierarchy on the panel:
            - a
              - d
                - e
              - f
            - b
              - g
              - h
            - c

            will return [
                         [a,
                           [d, [e]],
                           [f]],
                         [b, [g], [h]],
                         [c],
                        ]
            '''
            tree = []
            if isinstance(root, Window):
                tree.append(root.window.name)
            if root.expanded and root.children:
                for child in root.children:
                    tree.append(show_section_tree(child))
            return tree

        d = Layout.info(self)
        d["clients"] = sorted([x.name for x in self._nodes])
        d["sections"] = [x.title for x in self._tree.children]

        trees = {}
        for section in self._tree.children:
            trees[section.title] = show_section_tree(section)
        d["client_trees"] = trees
        return d

    def show(self, screen_rect):
        if not self._panel:
            self._create_panel(screen_rect)
        panel, body = screen_rect.hsplit(self.panel_width)
        self._resize_panel(panel)
        self._panel.unhide()

    def hide(self):
        if self._panel:
            self._panel.hide()

    def cmd_down(self):
        """Switch down in the window list"""
        win = None
        if self._focused:
            win = self._nodes[self._focused].get_next_window()
        if not win:
            win = self._tree.get_first_window()
        if win:
            self.group.focus(win.window, False)
        self._focused = win.window if win else None

    cmd_next = cmd_down

    def cmd_up(self):
        """Switch up in the window list"""
        win = None
        if self._focused:
            win = self._nodes[self._focused].get_prev_window()
        if not win:
            win = self._tree.get_last_window()
        if win:
            self.group.focus(win.window, False)
        self._focused = win.window if win else None

    cmd_previous = cmd_up

    def cmd_move_up(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx > 0:
            p[idx] = p[idx - 1]
            p[idx - 1] = node
        self.draw_panel()

    def cmd_move_down(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx < len(p) - 1:
            p[idx] = p[idx + 1]
            p[idx + 1] = node
        self.draw_panel()

    def cmd_move_left(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        if not isinstance(node.parent, Section):
            node.parent.children.remove(node)
            node.parent.parent.add(node)
        self.draw_panel()

    def cmd_add_section(self, name):
        """Add named section to tree"""
        self._tree.add_section(name)
        self.draw_panel()

    def cmd_del_section(self, name):
        """Add named section to tree"""
        self._tree.del_section(name)
        self.draw_panel()

    def cmd_section_up(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        snode = node
        while not isinstance(snode, Section):
            snode = snode.parent
        idx = snode.parent.children.index(snode)
        if idx > 0:
            node.parent.children.remove(node)
            snode.parent.children[idx - 1].add(node)
        self.draw_panel()

    def cmd_section_down(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        snode = node
        while not isinstance(snode, Section):
            snode = snode.parent
        idx = snode.parent.children.index(snode)
        if idx < len(snode.parent.children) - 1:
            node.parent.children.remove(node)
            snode.parent.children[idx + 1].add(node)
        self.draw_panel()

    def cmd_sort_windows(self, sorter, create_sections=True):
        """Sorts window to sections using sorter function

        Parameters
        ==========
        sorter : function with single arg returning string
            returns name of the section where window should be
        create_sections :
            if this parameter is True (default), if sorter returns unknown
            section name it will be created dynamically
        """
        for sec in self._tree.children:
            for win in sec.children[:]:
                nname = sorter(win.window)
                if nname is None or nname == sec.title:
                    continue
                try:
                    nsec = self._tree.sections[nname]
                except KeyError:
                    if create_sections:
                        self._tree.add_section(nname)
                        nsec = self._tree.sections[nname]
                    else:
                        continue
                sec.children.remove(win)
                nsec.children.append(win)
                win.parent = nsec
        self.draw_panel()

    def cmd_move_right(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        idx = node.parent.children.index(node)
        if idx > 0:
            node.parent.children.remove(node)
            node.parent.children[idx - 1].add(node)
        self.draw_panel()

    def cmd_expand_branch(self):
        if not self._focused:
            return
        self._nodes[self._focused].expanded = True
        self.draw_panel()

    def cmd_collapse_branch(self):
        if not self._focused:
            return
        self._nodes[self._focused].expanded = False
        self.draw_panel()

    def cmd_increase_ratio(self):
        self.panel_width += 10
        self.group.layout_all()

    def cmd_decrease_ratio(self):
        self.panel_width -= 10
        self.group.layout_all()

    def _create_drawer(self, screen_rect):
        if self._drawer is None:
            self._drawer = drawer.Drawer(
                self.group.qtile,
                self._panel.wid,
                self.panel_width,
                screen_rect.height
            )
        self._drawer.clear(self.bg_color)
        self._layout = self._drawer.textlayout(
            "",
            "ffffff",
            self.font,
            self.fontsize,
            self.fontshadow,
            wrap=False
        )

    def layout(self, windows, screen_rect):
        panel, body = screen_rect.hsplit(self.panel_width)
        self._resize_panel(panel)
        Layout.layout(self, windows, body)

    def _resize_panel(self, screen_rect):
        if self._panel:
            self._panel.place(
                screen_rect.x, screen_rect.y,
                screen_rect.width, screen_rect.height,
                0,
                None
            )
            self._create_drawer(screen_rect)
            self.draw_panel()
