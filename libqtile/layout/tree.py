# -*- coding: utf-8 -*-
from base import Layout
from .. import manager
from .. import window
from .. import drawer
from .. import hook

to_superscript = dict(zip(map(ord, u'0123456789'), map(ord, u'⁰¹²³⁴⁵⁶⁷⁸⁹')))

class TreeNode(object):

    def __init__(self):
        self.children = []
        self.expanded = True

    def add(self, node, hint):
        node.parent = self
        try:
            idx = self.children.index(hint)
        except ValueError:
            self.children.append(node)
        else:
            self.children.insert(idx+1, node)

    def draw(self, layout, top, level=0):
        self._children_start = top
        for i in self.children:
            top = i.draw(layout, top, level)
        self._children_stop = top
        return top

    def click(self, x, y):
        """Returns self or sibling which got the click"""
        if y >= self._children_stop or y < self._children_start:
            return
        for i in self.children:
            res = i.click(x, y)
            if res is not None:
                return res

    def add_superscript(self, title):
        if not self.expanded and self.children:
            return (unicode(len(self.children))
                .translate(to_superscript).encode('utf-8') + title)
        return title

    def get_first_window(self):
        if isinstance(self, Window):
            return self
        for i in self.children:
            node = i.get_first_window()
            if node:
                return node

    def get_last_window(self):
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
            for i in xrange(idx+1, len(parent.children)):
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
            for i in xrange(idx-1, -1, -1):
                res = parent.children[i].get_last_window()
                if res:
                    return res
            node = parent

class Root(TreeNode):

    def __init__(self, sections, default_section=None):
        super(Root, self).__init__()
        self.sections = {}
        for s in sections:
            node = Section(s)
            node.parent = self
            self.sections[s] = node
            self.children.append(node)
        if default_section is None:
            self.def_section = self.children[0]
        else:
            self.def_section = self.sections[default_section]

    def add(self, win, hint=None):
        sect = None
        parent = None
        if hint is not None:
            parent = hint.parent
        if parent is None:
            sect = getattr(win, 'tree_section', None)
        if sect is None:
            parent = self.sections.get(sect)
        if parent is None:
            parent = self.def_section
        node = Window(win)
        parent.add(node, hint=hint)
        return node

class Section(TreeNode):

    def __init__(self, title):
        super(Section, self).__init__()
        self.title = title

    def draw(self, layout, top, level=0):
        layout._layout.font_size = layout.section_fontsize
        layout._layout.text = self.add_superscript(self.title)
        layout._layout.colour = layout.section_fg
        del layout._layout.width  # no centering
        layout._drawer.draw_hbar(layout.section_fg,
            0, layout.panel_width, top, linewidth=1)
        layout._layout.draw(layout.section_left, top + layout.section_top)
        top += (layout._layout.height +
            layout.section_top + layout.section_padding)
        if self.expanded:
            top = super(Section, self).draw(layout, top, level)
        return top + layout.section_bottom

class Window(TreeNode):

    def __init__(self, win):
        super(Window, self).__init__()
        self.window = win

    def draw(self, layout, top, level=0):
        self._title_start = 0
        left = layout.padding_left + level*layout.level_shift
        layout._layout.font_size = layout.fontsize
        layout._layout.text = self.add_superscript(self.window.name)
        if self.window is layout._focused:
            fg = layout.active_fg
            bg = layout.active_bg
        else:
            fg = layout.inactive_fg
            bg = layout.inactive_bg
        layout._layout.colour = fg
        layout._layout.width = layout.panel_width - left
        framed = layout._layout.framed(layout.border_width, bg,
            layout.padding_x, layout.padding_y)
        framed.draw_fill(left, top)
        top += framed.height + layout.vspace + layout.border_width
        if self.expanded:
            return super(Window, self).draw(layout, top, level+1)
        return top

    def click(self, x, y):
        """Returns self if clicked on title else returns sibling"""
        if y >= self._title_start and y < self._children_start:
            return self
        return super(Window, self).click(x, y)

    def remove(self):
        self.parent.children.remove(self)
        if len(self.children) == 1:
            self.parent.add(self.children[0])
        elif self.children:
            head = self.children[0]
            self.parent.add(head)
            for i in self.children[1:]:
                head.add(i)
        del self.children

class TreeTab(Layout):
    """Tree Tab Layout

    This layout works just like Max but displays tree of the windows at the
    left border of the screen, which allows you to overview all opened windows.
    It's designed to work with ``uzbl-browser`` but works with other windows
    too.
    """

    name = "treetab"
    defaults = manager.Defaults(
        ("bg_color", "000000", "Background color of tabs"),
        ("active_bg", "000080", "Background color of active tab"),
        ("active_fg", "ffffff", "Foreground color of active tab"),
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
        ("font", "Arial", "Font"),
        ("fontsize", 14, "Font pixel size."),
        ("section_fontsize", 11, "Font pixel size of section label"),
        ("section_fg", "ffffff", "Color of section label"),
        ("section_top", 4, "Top margin of section label"),
        ("section_bottom", 6, "Bottom margin of section"),
        ("section_padding", 4, "Bottom of magin section label"),
        ("section_left", 4, "Left margin of section label"),
        ("panel_width", 150, "Width of the left panel"),
        ("sections", ['Default'],
            "Foreground color of inactive tab"),
    )

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self._focused = None
        self._panel = None
        self._tree = Root(self.sections)
        self._nodes = {}

    def clone(self, group):
        c = Layout.clone(self, group)
        c._focused = None
        c._panel = None
        c._tree = Root(self.sections)
        return c

    def focus_first(self):
        res = self._tree.get_first_window()
        if res:
            return res.window

    def focus_last(self):
        res = self._tree.get_last_window()
        if res:
            return res.window

    def focus_next(self, win):
        res = self._nodes[win].get_next_window()
        if res:
            return res.window

    def focus_prev(self, win):
        res = self._nodes[win].get_prev_window()
        if res:
            return res.window

    def focus(self, win):
        self._focused = win

    def blur(self):
        self._focused = None

    def add(self, win):
        if self._focused:
            node = self._tree.add(win, hint=self._nodes[self._focused])
        else:
            node = self._tree.add(win)
        self._nodes[win] = node

    def remove(self, win):
        res = self.focus_next(win)
        if self._focused is win:
            self._focused = None
        self._nodes[win].remove()
        del self._nodes[win]
        self.draw_panel()
        return res

    def _create_panel(self):
        self._panel = window.Internal.create(self.group.qtile,
            self.group.screen.dx,
            self.group.screen.dy,
            self.panel_width,
            self.group.screen.dheight)
        self._create_drawer()
        self._panel.handle_Expose = self._panel_Expose
        self._panel.handle_ButtonPress = self._panel_ButtonPress
        self.group.qtile.windowMap[self._panel.window.wid] = self._panel
        hook.subscribe.window_name_change(self.draw_panel)
        hook.subscribe.focus_change(self.draw_panel)

    def _panel_Expose(self, e):
        self.draw_panel()

    def draw_panel(self):
        if not self._panel:
            return
        self._drawer.clear(self.bg_color)
        self._tree.draw(self, 0)
        self._drawer.draw(0, self.panel_width)

    def _panel_ButtonPress(self, event):
        node = self._tree.click(event.event_x, event.event_y)
        if node:
            self.group.focus(node.window, False)

    def configure(self, c):
        if self._nodes and c is self._focused:
            c.place(
                self.group.screen.dx + self.panel_width,
                self.group.screen.dy,
                self.group.screen.dwidth - self.panel_width,
                self.group.screen.dheight,
                0,
                None
            )
            c.unhide()
        else:
            c.hide()

    def info(self):
        d = Layout.info(self)
        d["clients"] = [i.name for i in self._nodes]
        return d

    def show(self):
        if not self._panel:
            self._create_panel()
        self._panel.unhide()
        self.draw_panel()

    def hide(self):
        if self._panel:
            self._panel.hide()

    def cmd_down(self):
        """
            Switch down in the window list
        """
        win = self.focus_next(self._focused)
        if not win:
            win = self.focus_first()
        self.group.focus(win, False)

    def cmd_up(self):
        """
            Switch up in the window list
        """
        win = self.focus_prev(self._focused)
        if not win:
            win = self.focus_last()
        self.group.focus(win, False)

    def cmd_move_up(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx > 0:
            p[idx] = p[idx-1]
            p[idx-1] = node
        self.draw_panel()

    def cmd_move_down(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        p = node.parent.children
        idx = p.index(node)
        if idx < len(p)-1:
            p[idx] = p[idx+1]
            p[idx+1] = node
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
            snode.parent.children[idx-1].add(node)
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
        if idx < len(snode.parent.children)-1:
            node.parent.children.remove(node)
            snode.parent.children[idx+1].add(node)
        self.draw_panel()

    def cmd_move_right(self):
        win = self._focused
        if not win:
            return
        node = self._nodes[win]
        idx = node.parent.children.index(node)
        if idx > 0:
            node.parent.children.remove(node)
            node.parent.children[idx-1].add(node)
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
        self._resize_panel()
        self.group.layoutAll()

    def cmd_decrease_ratio(self):
        self.panel_width -= 10
        self._resize_panel()
        self.group.layoutAll()

    def _create_drawer(self):
        self._drawer = drawer.Drawer(self.group.qtile, self._panel.window.wid,
            self.panel_width, self.group.screen.dheight)
        self._drawer.clear(self.bg_color)
        self._layout = self._drawer.textlayout("", "ffffff", self.font,
            self.fontsize, wrap=False)

    def _resize_panel(self):
        if self._panel:
            self._panel.place(
                self.group.screen.dx,
                self.group.screen.dy,
                self.panel_width,
                self.group.screen.dheight,
                0,
                None
            )
            self._create_drawer()
            self.draw_panel()
