from .. import bar, hook, utils, manager
import base

class _GroupBase(base._Widget):
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    @property
    def fontsize(self):
        if self._fontsize is None:
            calc = self.bar.height - self.margin_y*2 - self.borderwidth*2 - self.padding*2
            return max(calc, 1)
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value

    def box_width(self, groups):
        width, height = self.drawer.max_layout_size(
            [i.name for i in groups],
            self.font,
            self.fontsize
        )
        return width + self.padding*2 + self.margin_x*2 + self.borderwidth*2

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout("", "ffffff", self.font, self.fontsize)
        self.setup_hooks()

    def setup_hooks(self):
        def hook_response(*args, **kwargs):
            self.bar.draw()
        hook.subscribe.client_managed(hook_response)
        hook.subscribe.client_urgent_hint_changed(hook_response)
        hook.subscribe.client_killed(hook_response)
        hook.subscribe.setgroup(hook_response)
        hook.subscribe.group_window_add(hook_response)

    def drawbox(self, offset, text, bordercolor, textcolor, rounded, block=False, width=None):
        self.layout.text = text
        self.layout.font_family = self.font
        self.layout.font_size = self.fontsize
        self.layout.colour = textcolor
        if width is not None:
            self.layout.width = width
        framed = self.layout.framed(self.borderwidth, bordercolor, self.padding, self.padding)
        if block:
            framed.draw_fill(offset, self.margin_y, rounded)
        else:
            framed.draw(offset, self.margin_y, rounded)


class AGroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = manager.Defaults(
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 3, "Current group border width"),
        ("font", "Arial", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("foreground", "aaaaaa", "Font colour"),
        ("background", "000000", "Widget background"),
        ("border", "215578", "Border colour"),
        ("padding", 5, "Padding inside the box")
    )
    def click(self, x, y, button):
        self.bar.screen.group.cmd_nextgroup()

    def calculate_width(self):
        return self.box_width(self.qtile.groups)

    def draw(self):
        self.drawer.clear(self.background)
        e = (i for i in self.qtile.groups if i.name == self.bar.screen.group.name ).next()
        self.drawbox(self.margin_x, e.name, self.border, self.foreground)
        self.drawer.draw(self.offset, self.width)


class GroupBox(_GroupBase):
    """
        A widget that graphically displays the current group.
    """
    defaults = manager.Defaults(
        ("active", "FFFFFF", "Active group font colour"),
        ("inactive", "404040", "Inactive group font colour"),
        ("urgent_text", "FF0000", "Urgent group font color"),
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 3, "Current group border width"),
        ("font", "Arial", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("background", "000000", "Widget background"),
        ("highlight_method", "border", "Method of highlighting (one of 'border' or 'block') \
                                        Uses *_border color settings"),
        ("rounded", True, "To round or not to round borders"),
        ("this_screen_border", "215578", "Border colour for group on this screen."),
        ("other_screen_border", "404040", "Border colour for group on other screen."),
        ("padding", 5, "Padding inside the box"),
        ("urgent_border", "FF0000", "Urgent border color"),
        ("urgent_alert_method", "border", "Method for alerting you of WM urgent " \
                                          "hints (one of 'border' or 'text')"),
    )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    def click(self, x, y, button):
        group = None
        curGroup = self.qtile.currentGroup
        if button == 5:
            group = curGroup.prevGroup()
        elif button == 4:
            group = curGroup.nextGroup()
        else:
            new_width = width = 0
            for g in self.qtile.groups:
                new_width += self.box_width([g])
                if x >= width and x <= new_width:
                    group = g
                    break
                width = new_width

        if group:
            self.bar.screen.setGroup(group)

    def calculate_width(self):
        width = 0
        for g in self.qtile.groups:
            width += self.box_width([g])
        return width

    def group_has_urgent(self, group):
        return len([w for w in group.windows if w.urgent]) > 0

    def draw(self):
        self.drawer.clear(self.background)

        offset = 0
        for i, g in enumerate(self.qtile.groups):
            bw = self.box_width([g])
            if g.screen:
                if self.bar.screen.group.name == g.name:
                    border = self.this_screen_border
                else:
                    border = self.other_screen_border
            elif self.group_has_urgent(g) and self.urgent_alert_method == "border":
                border = self.urgent_border
            else:
                border = self.background

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
                self.highlight_method == 'block' and True or False,
                bw - self.margin_x*2 - self.padding*2
            )
            offset += bw
        self.drawer.draw(self.offset, self.width)


