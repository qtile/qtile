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
from functools import partial
from typing import Any

from libqtile import hook
from libqtile.widget import base


class _GroupBase(base._TextBox, base.PaddingMixin, base.MarginMixin):
    defaults: list[tuple[str, Any, str]] = [
        ("borderwidth", 3, "Current group border width"),
        ("center_aligned", True, "center-aligned group box"),
        ("markup", False, "Whether or not to use pango markup"),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(_GroupBase.defaults)

    def box_width(self, groups):
        width, _ = self.drawer.max_layout_size(
            [self.fmt.format(i.label) for i in groups], self.font, self.fontsize, self.markup
        )
        return width + self.padding_x * 2 + self.borderwidth * 2

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if self.fontsize is None:
            calc = self.bar.size - self.margin_y * 2 - self.borderwidth * 2 - self.padding_y * 2
            self.fontsize = max(calc, 1)

        self.layout = self.drawer.textlayout(
            "", "ffffff", self.font, self.fontsize, self.fontshadow, markup=self.markup
        )
        self.setup_hooks()

    def _hook_response(self, *args, **kwargs):
        self.bar.draw()

    def setup_hooks(self):
        hook.subscribe.client_managed(self._hook_response)
        hook.subscribe.client_urgent_hint_changed(self._hook_response)
        hook.subscribe.client_killed(self._hook_response)
        hook.subscribe.setgroup(self._hook_response)
        hook.subscribe.group_window_add(self._hook_response)
        hook.subscribe.current_screen_change(self._hook_response)
        hook.subscribe.changegroup(self._hook_response)

    def remove_hooks(self):
        hook.unsubscribe.client_managed(self._hook_response)
        hook.unsubscribe.client_urgent_hint_changed(self._hook_response)
        hook.unsubscribe.client_killed(self._hook_response)
        hook.unsubscribe.setgroup(self._hook_response)
        hook.unsubscribe.group_window_add(self._hook_response)
        hook.unsubscribe.current_screen_change(self._hook_response)
        hook.unsubscribe.changegroup(self._hook_response)

    def drawbox(
        self,
        offset,
        text,
        bordercolor,
        textcolor,
        highlight_color=None,
        width=None,
        rounded=False,
        block=False,
        line=False,
        highlighted=False,
    ):
        self.layout.text = self.fmt.format(text)
        self.layout.colour = textcolor
        if width is not None:
            self.layout.width = width
        if line:
            pad_y = [
                (self.bar.size - self.layout.height - self.borderwidth) / 2,
                (self.bar.size - self.layout.height + self.borderwidth) / 2,
            ]
        else:
            pad_y = self.padding_y

        if bordercolor is None:
            # border colour is set to None when we don't want to draw a border at all
            # Rather than dealing with alpha blending issues, we just set border width
            # to 0.
            border_width = 0
            framecolor = self.background or self.bar.background
        else:
            border_width = self.borderwidth
            framecolor = bordercolor

        framed = self.layout.framed(border_width, framecolor, 0, pad_y, highlight_color)
        y = self.margin_y
        if self.center_aligned:
            y += (self.bar.size - framed.height) / 2 - self.margin_y
        if block and bordercolor is not None:
            framed.draw_fill(offset, y, rounded)
        elif line:
            framed.draw_line(offset, y, highlighted)
        else:
            framed.draw(offset, y, rounded)

    def finalize(self):
        self.remove_hooks()
        base._TextBox.finalize(self)


class AGroupBox(_GroupBase):
    """A widget that graphically displays the current group"""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [("border", "000000", "group box border color")]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(AGroupBox.defaults)

    def _configure(self, qtile, bar):
        _GroupBase._configure(self, qtile, bar)
        self.add_callbacks({"Button1": partial(self.bar.screen.next_group, warp=False)})

    def calculate_length(self):
        return self.box_width(self.qtile.groups) + self.margin_x * 2

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        e = next(i for i in self.qtile.groups if i.name == self.bar.screen.group.name)
        self.drawbox(self.margin_x, e.name, self.border, self.foreground)
        self.draw_at_default_position()


class GroupBox(_GroupBase):
    """
    A widget that graphically displays the current group.
    All groups are displayed by their label.
    If the label of a group is the empty string that group will not be displayed.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("block_highlight_text_color", None, "Selected group font colour"),
        ("active", "FFFFFF", "Active group font colour"),
        ("inactive", "404040", "Inactive group font colour"),
        (
            "highlight_method",
            "border",
            "Method of highlighting ('border', 'block', 'text', or 'line')"
            "Uses `*_border` color settings",
        ),
        ("rounded", True, "To round or not to round box borders"),
        (
            "this_current_screen_border",
            "215578",
            "Border or line colour for group on this screen when focused.",
        ),
        (
            "this_screen_border",
            "215578",
            "Border or line colour for group on this screen when unfocused.",
        ),
        (
            "other_current_screen_border",
            "404040",
            "Border or line colour for group on other screen when focused.",
        ),
        (
            "other_screen_border",
            "404040",
            "Border or line colour for group on other screen when unfocused.",
        ),
        (
            "highlight_color",
            ["000000", "282828"],
            "Active group highlight color when using 'line' highlight method.",
        ),
        (
            "urgent_alert_method",
            "border",
            "Method for alerting you of WM urgent "
            "hints (one of 'border', 'text', 'block', or 'line')",
        ),
        ("urgent_text", "FF0000", "Urgent group font color"),
        ("urgent_border", "FF0000", "Urgent border or line color"),
        ("disable_drag", False, "Disable dragging and dropping of group names on widget"),
        ("invert_mouse_wheel", False, "Whether to invert mouse wheel group movement"),
        ("use_mouse_wheel", True, "Whether to use mouse wheel events"),
        (
            "visible_groups",
            None,
            "Groups that will be visible. "
            "If set to None or [], all groups will be visible."
            "Visible groups are identified by name not by their displayed label.",
        ),
        (
            "hide_unused",
            False,
            "Hide groups that have no windows and that are not displayed on any screen.",
        ),
        ("spacing", None, "Spacing between groups(if set to None, will be equal to margin_x)"),
        ("toggle", True, "Enable toggling of group when clicking on same group name"),
    ]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(GroupBox.defaults)
        self.clicked = None
        self.click = None

        default_callbacks = {"Button1": self.select_group}
        if self.use_mouse_wheel:
            default_callbacks.update(
                {
                    "Button5" if self.invert_mouse_wheel else "Button4": self.prev_group,
                    "Button4" if self.invert_mouse_wheel else "Button5": self.next_group,
                }
            )
        self.add_callbacks(default_callbacks)

    def _configure(self, qtile, bar):
        _GroupBase._configure(self, qtile, bar)
        if self.spacing is None:
            self.spacing = self.margin_x

    @property
    def groups(self):
        """
        returns list of visible groups.
        The existing groups are filtered by the visible_groups attribute and
        their label. Groups with an empty string as label are never contained.
        Groups that are not named in visible_groups are not returned.
        """
        groups = filter(lambda g: g.label, self.qtile.groups)

        if self.hide_unused:
            groups = filter(lambda g: g.windows or g.screen, groups)

        if self.visible_groups:
            groups = filter(lambda g: g.name in self.visible_groups, groups)

        return list(groups)

    def get_clicked_group(self):
        group = None
        new_width = self.margin_x - self.spacing / 2.0
        width = 0
        for g in self.groups:
            new_width += self.box_width([g]) + self.spacing
            if width <= self.click <= new_width:
                group = g
                break
            width = new_width
        return group

    def button_press(self, x, y, button):
        self.click = x
        _GroupBase.button_press(self, x, y, button)

    def next_group(self):
        group = None
        current_group = self.qtile.current_group
        i = itertools.cycle(self.qtile.groups)
        while next(i) != current_group:
            pass
        while group is None or group not in self.groups:
            group = next(i)
        self.go_to_group(group)

    def prev_group(self):
        group = None
        current_group = self.qtile.current_group
        i = itertools.cycle(reversed(self.qtile.groups))
        while next(i) != current_group:
            pass
        while group is None or group not in self.groups:
            group = next(i)
        self.go_to_group(group)

    def select_group(self):
        self.clicked = None
        group = self.get_clicked_group()
        if not self.disable_drag:
            self.clicked = group
        self.go_to_group(group)

    def go_to_group(self, group):
        if group:
            if self.bar.screen.group != group or not self.disable_drag or not self.toggle:
                self.bar.screen.set_group(group, warp=False)
            else:
                self.bar.screen.toggle_group(group, warp=False)

    def button_release(self, x, y, button):
        self.click = x
        if button not in (5, 4):
            group = self.get_clicked_group()
            if group and self.clicked:
                group.switch_groups(self.clicked.name)
                self.clicked = None

    def calculate_length(self):
        width = self.margin_x * 2 + (len(self.groups) - 1) * self.spacing
        for g in self.groups:
            width += self.box_width([g])
        return width

    def group_has_urgent(self, group):
        return any(w.urgent for w in group.windows)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        offset = self.margin_x
        for i, g in enumerate(self.groups):
            to_highlight = False
            is_block = self.highlight_method == "block"
            is_line = self.highlight_method == "line"

            bw = self.box_width([g])

            if self.group_has_urgent(g) and self.urgent_alert_method == "text":
                text_color = self.urgent_text
            elif g.windows:
                text_color = self.active
            else:
                text_color = self.inactive

            if g.screen:
                if self.highlight_method == "text":
                    border = None
                    text_color = self.this_current_screen_border
                else:
                    if self.block_highlight_text_color:
                        text_color = self.block_highlight_text_color
                    if self.bar.screen.group.name == g.name:
                        if self.qtile.current_screen == self.bar.screen:
                            border = self.this_current_screen_border
                            to_highlight = True
                        else:
                            border = self.this_screen_border
                    else:
                        if self.qtile.current_screen == g.screen:
                            border = self.other_current_screen_border
                        else:
                            border = self.other_screen_border
            elif self.group_has_urgent(g) and self.urgent_alert_method in (
                "border",
                "block",
                "line",
            ):
                border = self.urgent_border
                if self.urgent_alert_method == "block":
                    is_block = True
                elif self.urgent_alert_method == "line":
                    is_line = True
            else:
                border = None

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
                highlighted=to_highlight,
            )
            offset += bw + self.spacing
        self.draw_at_default_position()
