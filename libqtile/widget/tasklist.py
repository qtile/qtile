from .. import bar, hook, manager
import base

class TaskList(base._Widget):
    defaults = manager.Defaults(
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 2, "Current group border width"),
        ("font", "Arial", "Font face"),
        ("fontsize", None, "Font pixel size - calculated if None"),
        ("foreground", "ffffff", "Font colour"),
        ("background", None, "Widget background"),
        ("border", "215578", "Border colour"),
        ("padding", 5, "Padding inside the box"),
        ("rounded", True, "To round or not to round borders"),
        ("highlight_method", "border",
         "Method of highlighting (one of 'border' or 'block') "
         "Uses *_border color settings"),
        ("urgent_border", "FF0000",
         "Urgent border color"),
        ("urgent_alert_method", "border",
         "Method for alerting you of WM urgent "
         "hints (one of 'border' or 'text')"),
    )

    def __init__(self, **config):
        base._Widget.__init__(self, bar.STRETCH, **config)

    @property
    def fontsize(self):
        if self._fontsize is None:
            calc = (self.bar.height - self.margin_y * 2 -
                    self.borderwidth * 2 - self.padding * 2)
            return max(calc, 1)
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value

    def box_width(self, text):
        width, _ = self.drawer.max_layout_size(
            [text],
            self.font,
            self.fontsize
        )
        return (width + self.padding * 2 +
                self.margin_x * 2 + self.borderwidth * 2)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            "", "ffffff", self.font, self.fontsize)
        self.setup_hooks()

    def update(self, *args, **argvs):
        self.bar.draw()

    def setup_hooks(self):
        hook.subscribe.window_name_change(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)
        hook.subscribe.client_urgent_hint_changed(self.update)

    def drawtext(self, text, textcolor, width):
        self.layout.text = text
        self.layout.font_family = self.font
        self.layout.font_size = self.fontsize
        self.layout.colour = textcolor
        if width is not None:
            self.layout.width = width

    def drawbox(self, offset, text, bordercolor, textcolor, rounded=False,
                block=False, width=None):
        self.drawtext(text, textcolor, width)
        framed = self.layout.framed(self.borderwidth, bordercolor,
                                    self.padding, self.padding)
        if block:
            framed.draw_fill(offset, self.margin_y, rounded)
        else:
            framed.draw(offset, self.margin_y, rounded)

    def get_clicked(self, x, y):
        window = None
        new_width = width = 0
        for w in self.bar.screen.group.windows:
            new_width += self.box_width(w.name)
            if x >= width and x <= new_width:
                window = w
                break
            width = new_width
        return window

    def button_press(self, x, y, button):
        window = None
        current_win = self.bar.screen.group.currentWindow

        # TODO: support scroll
        if button == 1:
            window = self.get_clicked(x, y)

        if window and window is not current_win:
            window.group.focus(window, False)
            if window.floating:
                window.cmd_bring_to_front()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        offset = 0

        for w in self.bar.screen.group.windows:
            state = ''
            if w is None:
                pass
            elif w.maximized:
                state = '[] '
            elif w.minimized:
                state = '_ '
            elif w.floating:
                state = 'V '
            task = "%s%s" % (state,  w.name if w and w.name else " ")

            if w.urgent:
                border = "FF0000"
            elif w is w.group.currentWindow:
                border = self.border
            else:
                border = self.background or self.bar.background

            bw = self.box_width(task)
            self.drawbox(
                self.margin_x + offset,
                task,
                border,
                self.foreground,
                self.rounded,
                self.highlight_method == 'block',
                bw - self.margin_x * 2 - self.padding * 2
            )

            offset += bw
        self.drawer.draw(self.offset, self.width)
