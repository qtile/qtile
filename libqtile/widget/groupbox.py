# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2009 Ben Duffield
# Copyright (c) 2010 aldo
# Copyright (c) 2010-2012 roger
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011-2015 Tycho Andersen
# Copyright (c) 2012-2013 dequis
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Filipe Nepomuceno
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

import itertools

from .. import bar, hook
from . import base

try:
    from typing import Any, List, Tuple  # noqa: F401
except ImportError:
    pass


class _GroupBase(base._TextBox, base.PaddingMixin, base.MarginMixin):
    defaults = [
        ("borderwidth", 3, "Current group border width"),
        ("center_aligned", False, "center-aligned group box"),
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, **config):
        base._TextBox.__init__(self, width=bar.CALCULATED, **config)
        self.add_defaults(_GroupBase.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.add_defaults(base.MarginMixin.defaults)

    def box_width(self, groups):
        width, _ = self.drawer.max_layout_size(
            [i.label for i in groups],
            self.font,
            self.fontsize
        )
        return width + self.padding_x * 2 + self.borderwidth * 2

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if self.fontsize is None:
            calc = self.bar.height - self.margin_y * 2 - \
                self.borderwidth * 2 - self.padding_y * 2
            self.fontsize = max(calc, 1)

        self.layout = self.drawer.textlayout(
            "",
            "ffffff",
            self.font,
            self.fontsize,
            self.fontshadow
        )
        self.setup_hooks()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.bar.draw()
        hook.subscribe.client_managed(hook_response)
        hook.subscribe.client_urgent_hint_changed(hook_response)
        hook.subscribe.client_killed(hook_response)
        hook.subscribe.setgroup(hook_response)
        hook.subscribe.group_window_add(hook_response)
        hook.subscribe.current_screen_change(hook_response)
        hook.subscribe.changegroup(hook_response)

    def drawbox(self, offset, text, bordercolor, textcolor, highlight_color=None,
                width=None, rounded=False, block=False, line=False, highlighted=False):
        self.layout.text = text
        self.layout.font_family = self.font
        self.layout.font_size = self.fontsize
        self.layout.colour = textcolor
        if width is not None:
            self.layout.width = width
        if line:
            pad_y = [
                (self.bar.height - self.layout.height - self.borderwidth) / 2,
                (self.bar.height - self.layout.height + self.borderwidth) / 2
            ]
        else:
            pad_y = self.padding_y
        framed = self.layout.framed(
            self.borderwidth,
            bordercolor,
            0,
            pad_y,
            highlight_color
        )
        y = self.margin_y
        if self.center_aligned:
            for t in base.MarginMixin.defaults:
                if t[0] == 'margin':
                    y += (self.bar.height - framed.height) / 2 - t[1]
                    break
        if block:
            framed.draw_fill(offset, y, rounded)
        elif line:
            framed.draw_line(offset, y, highlighted)
        else:
            framed.draw(offset, y, rounded)


class AGroupBox(_GroupBase):
    """A widget that graphically displays the current group"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [("border", "000000", "group box border color")]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(AGroupBox.defaults)

    def button_press(self, x, y, button):
        self.bar.screen.cmd_next_group()

    def calculate_length(self):
        return self.box_width(self.qtile.groups) + self.margin_x * 2

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        e = next(
            i for i in self.qtile.groups
            if i.name == self.bar.screen.group.name
        )
        self.drawbox(self.margin_x, e.name, self.border, self.foreground)
        self.drawer.draw(offsetx=self.offset, width=self.width)


class GroupBox(_GroupBase):
    """
    A widget that graphically displays the current group.
    All groups are displayed by their label.
    If the label of a group is the empty string that group will not be displayed.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("active", "FFFFFF", "Active group font colour"),
        ("inactive", "404040", "Inactive group font colour"),
        (
            "highlight_method",
            "border",
            "Method of highlighting ('border', 'block', 'text', or 'line')"
            "Uses *_border color settings"
        ),
        ("rounded", True, "To round or not to round box borders"),
        (
            "this_current_screen_border",
            "215578",
            "Border or line colour for group on this screen when focused."
        ),
        (
            "this_screen_border",
            "215578",
            "Border or line colour for group on this screen when unfocused."
        ),
        (
            "other_current_screen_border",
            "404040",
            "Border or line colour for group on other screen when focused."
        ),
        (
            "other_screen_border",
            "404040",
            "Border or line colour for group on other screen when unfocused."
        ),
        (
            "highlight_color",
            ["000000", "282828"],
            "Active group highlight color when using 'line' highlight method."
        ),
        (
            "urgent_alert_method",
            "border",
            "Method for alerting you of WM urgent "
            "hints (one of 'border', 'text', 'block', or 'line')"
        ),
        ("urgent_text", "FF0000", "Urgent group font color"),
        ("urgent_border", "FF0000", "Urgent border or line color"),
        (
            "disable_drag",
            False,
            "Disable dragging and dropping of group names on widget"
        ),
        ("invert_mouse_wheel", False, "Whether to invert mouse wheel group movement"),
        ("use_mouse_wheel", True, "Whether to use mouse wheel events"),
        (
            "visible_groups",
            None,
            "Groups that will be visible. "
            "If set to None or [], all groups will be visible."
            "Visible groups are identified by name not by their displayed label."
        ),
        (
            "spacing",
            None,
            "Spacing between groups"
            "(if set to None, will be equal to margin_x)")
    ]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(GroupBox.defaults)
        if self.spacing is None:
            self.spacing = self.margin_x
        self.clicked = None

    @property
    def groups(self):
        """
        returns list of visible groups.
        The existing groups are filtered by the visible_groups attribute and
        their label. Groups with an empty string as label are never contained.
        Groups that are not named in visible_groups are not returned.
        """
        if self.visible_groups:
            return [g for g in self.qtile.groups
                    if g.label and g.name in self.visible_groups]
        else:
            return [g for g in self.qtile.groups if g.label]

    def get_clicked_group(self, x, y):
        group = None
        new_width = self.margin_x - self.spacing / 2.0
        width = 0
        for g in self.groups:
            new_width += self.box_width([g]) + self.spacing
            if width <= x <= new_width:
                group = g
                break
            width = new_width
        return group

    def button_press(self, x, y, button):
        self.clicked = None
        group = None
        curGroup = self.qtile.currentGroup

        if button == (5 if not self.invert_mouse_wheel else 4):
            if self.use_mouse_wheel:
                i = itertools.cycle(self.qtile.groups)
                while next(i) != curGroup:
                    pass
                while group is None or group not in self.groups:
                    group = next(i)
        elif button == (4 if not self.invert_mouse_wheel else 5):
            if self.use_mouse_wheel:
                i = itertools.cycle(reversed(self.qtile.groups))
                while next(i) != curGroup:
                    pass
                while group is None or group not in self.groups:
                    group = next(i)
        else:
            group = self.get_clicked_group(x, y)
            if not self.disable_drag:
                self.clicked = group

        if group:
            self.bar.screen.setGroup(group)

    def button_release(self, x, y, button):
        if button not in (5, 4):
            group = self.get_clicked_group(x, y)
            if group and self.clicked:
                group.cmd_switch_groups(self.clicked.name)
                self.clicked = None

    def calculate_length(self):
        width = self.margin_x * 2 + (len(self.groups) - 1) * self.spacing
        for g in self.groups:
            width += self.box_width([g])
        return width

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        offset = self.margin_x
        for i, g in enumerate(self.groups):
            to_highlight = False
            is_block = (self.highlight_method == 'block')
            is_line = (self.highlight_method == 'line')

            bw = self.box_width([g])

            if self.group_has_urgent(g) and self.urgent_alert_method == "text":
                text_color = self.urgent_text
            elif g.windows:
                text_color = self.active
            else:
                text_color = self.inactive

            if g.screen:
                if self.highlight_method == 'text':
                    border = self.bar.background
                    text_color = self.this_current_screen_border
                else:
                    if self.bar.screen.group.name == g.name:
                        if self.qtile.currentScreen == self.bar.screen:
                            border = self.this_current_screen_border
                            to_highlight = True
                        else:
                            border = self.this_screen_border
                    else:
                        if self.qtile.currentScreen == g.screen:
                            border = self.other_current_screen_border
                        else:
                            border = self.other_screen_border
            elif self.group_has_urgent(g) and \
                    self.urgent_alert_method in ('border', 'block', 'line'):
                border = self.urgent_border
                if self.urgent_alert_method == 'block':
                    is_block = True
                elif self.urgent_alert_method == 'line':
                    is_line = True
            else:
                border = self.background or self.bar.background

            self.drawbox(
                offset,
                g.label,
                border,
                text_color,
                highlight_color=self.highlight_color,
                width=bw,
                rounded=self.rounded,
                block=is_block,
                line=is_line,
                highlighted=to_highlight
            )
            offset += bw + self.spacing
        self.drawer.draw(offsetx=self.offset, width=self.width)
