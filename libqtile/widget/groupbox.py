from .. import bar, hook
import base


class _GroupBase(base._TextBox, base.PaddingMixin, base.MarginMixin):
    defaults = [
        ("borderwidth", 3, "Current group border width"),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(_GroupBase.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.add_defaults(base.MarginMixin.defaults)

    def box_width(self, groups):
        width, height = self.drawer.max_layout_size(
            [i.name for i in groups],
            self.font,
            self.fontsize
        )
        return width + self.padding_x * 2 + self.margin_x * 2 + \
            self.borderwidth * 2

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

    def drawbox(self, offset, text, bordercolor, textcolor, rounded=False,
                block=False, width=None):
        self.layout.text = text
        self.layout.font_family = self.font
        self.layout.font_size = self.fontsize
        self.layout.colour = textcolor
        if width is not None:
            self.layout.width = width
        framed = self.layout.framed(
            self.borderwidth,
            bordercolor,
            self.padding_x,
            self.padding_y
        )
        if block:
            framed.draw_fill(offset, self.margin_y, rounded)
        else:
            framed.draw(offset, self.margin_y, rounded)


class AGroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = [("border", "000000", "group box border color")]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(AGroupBox.defaults)

    def button_press(self, x, y, button):
        self.bar.screen.cmd_nextgroup()

    def calculate_width(self):
        return self.box_width(self.qtile.groups)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        e = (
            i for i in self.qtile.groups
            if i.name == self.bar.screen.group.name
        ).next()
        self.drawbox(self.margin_x, e.name, self.border, self.foreground)
        self.drawer.draw(self.offset, self.width)


class GroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = [
        ("active", "FFFFFF", "Active group font colour"),
        ("inactive", "404040", "Inactive group font colour"),
        ("urgent_text", "FF0000", "Urgent group font color"),
        (
            "highlight_method",
            "border",
            "Method of highlighting (one of 'border' or 'block') "
            "Uses *_border color settings"
        ),
        ("rounded", True, "To round or not to round borders"),
        (
            "this_current_screen_border",
            "215578",
            "Border colour for group on this screen when focused."
        ),
        (
            "urgent_alert_method",
            "border",
            "Method for alerting you of WM urgent "
            "hints (one of 'border', 'text' or 'block')"
        ),
        (
            "disable_drag",
            False,
            "Disable dragging and dropping of group names on widget"
        ),
        (
            "this_screen_border",
            "215578",
            "Border colour for group on this screen."
        ),
        (
            "other_screen_border",
            "404040",
            "Border colour for group on other screen."
        ),
        ("urgent_border", "FF0000", "Urgent border color"),
        ("invert_mouse_wheel", False, "Whether to invert mouse wheel group movement")
    ]

    def __init__(self, **config):
        _GroupBase.__init__(self, **config)
        self.add_defaults(GroupBox.defaults)
        self.clicked = None

    def get_clicked_group(self, x, y):
        group = None
        new_width = 0
        width = 0
        for g in self.qtile.groups:
            new_width += self.box_width([g])
            if x >= width and x <= new_width:
                group = g
                break
            width = new_width
        return group

    def button_press(self, x, y, button):
        self.clicked = None
        group = None
        curGroup = self.qtile.currentGroup

        if button == (5 if not self.invert_mouse_wheel else 4):
            group = curGroup.prevGroup()
        elif button == (4 if not self.invert_mouse_wheel else 5):
            group = curGroup.nextGroup()
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

    def calculate_width(self):
        width = 0
        for g in self.qtile.groups:
            width += self.box_width([g])
        return width

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        offset = 0
        for i, g in enumerate(self.qtile.groups):
            is_block = (self.highlight_method == 'block')

            bw = self.box_width([g])
            if g.screen:
                if self.bar.screen.group.name == g.name:
                    if self.qtile.currentScreen == self.bar.screen:
                        border = self.this_current_screen_border
                    else:
                        border = self.this_screen_border
                else:
                    border = self.other_screen_border
            elif self.group_has_urgent(g) and \
                    self.urgent_alert_method in ('border', 'block'):
                border = self.urgent_border
                if self.urgent_alert_method == 'block':
                    is_block = True
            else:
                border = self.background or self.bar.background

            if self.group_has_urgent(g) and self.urgent_alert_method == "text":
                text = self.urgent_text
            elif g.windows:
                text = self.active
            else:
                text = self.inactive

            self.drawbox(
                self.margin_x + offset,
                g.name,
                border,
                text,
                self.rounded,
                is_block,
                bw - self.margin_x * 2 - self.padding_x * 2
            )
            offset += bw
        self.drawer.draw(self.offset, self.width)
