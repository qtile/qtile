import cairo
from .. import bar, hook, manager
import base

class TaskList(base._Widget):
    defaults = [
        ("margin_y", 3, "Y margin outside the box"),
        ("margin_x", 3, "X margin outside the box"),
        ("borderwidth", 2, "Current group border width"),
        ("border", "215578", "Border colour"),
        ("rounded", True, "To round or not to round borders"),
        ("highlight_method", "border",
         "Method of highlighting (one of 'border' or 'block') "
         "Uses *_border color settings"),
        ("urgent_border", "FF0000",
         "Urgent border color"),
        ("urgent_alert_method", "border",
         "Method for alerting you of WM urgent "
         "hints (one of 'border' or 'text')"),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.STRETCH, **config)
        self.add_defaults(TaskList.defaults)
        self._icons_cache = {}

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
        self.icon_size = self.bar.height - (self.borderwidth+2) * 2

        if self.fontsize is None:
            calc = (self.bar.height - self.margin_y * 2 -
                    self.borderwidth * 2 - self.padding * 2)
            self.fontsize = max(calc, 1)
        self.layout = self.drawer.textlayout(
            "", "ffffff", self.font, self.fontsize, self.fontshadow)
        self.setup_hooks()

    def update(self, window=None):
        group = self.bar.screen.group
        if not window or window and window.group is group:
            self.bar.draw()

    def remove_icon_cache(self, window):
        wid = window.window.wid
        if wid in self._icons_cache:
            self._icons_cache.pop(wid)

    def invalidate_cache(self, window):
        self.remove_icon_cache(window)
        self.update(window)

    def setup_hooks(self):
        hook.subscribe.window_name_change(self.update)
        hook.subscribe.focus_change(self.update)
        hook.subscribe.float_change(self.update)
        hook.subscribe.client_urgent_hint_changed(self.update)

        hook.subscribe.net_wm_icon_change(self.invalidate_cache)
        hook.subscribe.client_killed(self.remove_icon_cache)

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
        padding_x = [self.padding + self.icon_size+4, self.padding]
        framed = self.layout.framed(self.borderwidth, bordercolor,
                                    padding_x, self.padding)
        if block:
            framed.draw_fill(offset, self.margin_y, rounded)
        else:
            framed.draw(offset, self.margin_y, rounded)

    def get_clicked(self, x, y):
        window = None
        new_width = width = 0
        for w in self.bar.screen.group.windows:
            new_width += self.icon_size+self.box_width(w.name)
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

    def get_window_icon(self, window):
        cache = self._icons_cache.get(window.window.wid)
        if cache:
            return cache

        icons = sorted(window.icons.iteritems(),
                key=lambda x: abs(self.icon_size-int(x[0].split("x")[0])))
        icon = icons[0]
        width, height = map(int, icon[0].split("x"))

        img = cairo.ImageSurface.create_for_data(icon[1],
                        cairo.FORMAT_ARGB32, width, height)

        surface = cairo.SurfacePattern(img)

        scaler = cairo.Matrix()

        if height != self.icon_size:
            sp = height / float(self.icon_size)
            height = self.icon_size
            width = width / sp
            scaler.scale(sp, sp)
        surface.set_matrix(scaler)
        self._icons_cache[window.window.wid] = surface
        return surface

    def draw_icon(self, window, offset):
        if not window.icons:
            return

        x = offset + self.padding + self.borderwidth + 2 + self.margin_x
        y = self.padding + self.borderwidth

        surface = self.get_window_icon(window)

        self.drawer.ctx.save()
        self.drawer.ctx.translate(x, y)
        self.drawer.ctx.set_source(surface)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

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
                border = self.urgent_border
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
            self.draw_icon(w, offset)

            offset += bw + self.icon_size
        self.drawer.draw(self.offset, self.width)
