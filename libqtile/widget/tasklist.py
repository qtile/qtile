# Copyright (c) 2012-2014 roger
# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2013 dequis
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
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

from __future__ import division

import cairocffi
from .. import bar, hook
from . import base


class TaskList(base._Widget, base.PaddingMixin, base.MarginMixin):
    """Displays the icon and name of each window in the current group

    Contrary to WindowTabs this is an interactive widget.  The window that
    currently has focus is highlighted.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size. Calculated if None."),
        ("foreground", "ffffff", "Foreground colour"),
        (
            "fontshadow",
            None,
            "font shadow color, default is None(no shadow)"
        ),
        ("borderwidth", 2, "Current group border width"),
        ("border", "215578", "Border colour"),
        ("rounded", True, "To round or not to round borders"),
        (
            "highlight_method",
            "border",
            "Method of highlighting (one of 'border' or 'block') "
            "Uses \*_border color settings"
        ),
        ("urgent_border", "FF0000", "Urgent border color"),
        (
            "urgent_alert_method",
            "border",
            "Method for alerting you of WM urgent "
            "hints (one of 'border' or 'text')"
        ),
        (
            "unfocused_border",
            None,
            "Border color for unfocused windows. "
            "Affects only hightlight_method 'border' and 'block'. "
            "Defaults to None, which means no special color."
        ),
        (
            "max_title_width",
            None,
            "Max size in pixels of task title."
            "(if set to None, as much as available.)"
        ),
        (
            "spacing",
            None,
            "Spacing between tasks."
            "(if set to None, will be equal to margin_x)"
        ),
        (
            'txt_minimized',
            '_ ',
            'Text representation of the minimized window state. '
            'e.g., "_ " or "\U0001F5D5 "'
        ),
        (
            'txt_maximized',
            '[] ',
            'Text representation of the maximized window state. '
            'e.g., "[] " or "\U0001F5D6 "'
        ),
        (
            'txt_floating',
            'V ',
            'Text representation of the floating window state. '
            'e.g., "V " or "\U0001F5D7 "'
        ),
        (
            'icon_size',
            None,
            'Icon size. '
            '(Calculated if set to None. Icons are hidden if set to 0.)'
        ),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.STRETCH, **config)
        self.add_defaults(TaskList.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        self._icons_cache = {}
        self._box_end_positions = []
        if self.spacing is None:
            self.spacing = self.margin_x

    def box_width(self, text):
        """
        calculate box width for given text.
        If max_title_width is given, the returned width is limited to it.
        """
        width, _ = self.drawer.max_layout_size(
            [text],
            self.font,
            self.fontsize
        )
        width = width + 2 * (self.padding_x + self.borderwidth)
        return width

    def get_taskname(self, window):
        """
        Get display name for given window.
        Depending on its state minimized, maximized and floating
        appropriate characters are prepended.
        """
        state = ''
        if window is None:
            pass
        elif window.minimized:
            state = self.txt_minimized
        elif window.maximized:
            state = self.txt_maximized
        elif window.floating:
            state = self.txt_floating

        return "%s%s" % (state, window.name if window and window.name else "?")

    @property
    def windows(self):
        return self.bar.screen.group.windows

    def calc_box_widths(self):
        """
        Calculate box width for each window in current group.
        If the available space is less than overall size of boxes,
        the boxes are shrunk by percentage if greater than average.
        """
        windows = self.windows
        window_count = len(windows)

        # if no windows present for current group just return empty list
        if not window_count:
            return []

        # Determine available and max average width for task name boxes.
        width_total = (self.width - 2 * self.margin_x -
                       (window_count - 1) * self.spacing)
        width_avg = width_total / window_count

        names = [self.get_taskname(w) for w in windows]

        if self.icon_size == 0:
            icons = len(windows) * [None]
        else:
            icons = [self.get_window_icon(w) for w in windows]

        # calculated width for each task according to icon and task name
        # consisting of state abbreviation and window name
        # Obey max_title_width if specified
        width_boxes = [(self.box_width(names[idx]) +
                        ((self.icon_size + self.padding_x) if icons[idx] else 0))
                       for idx in range(window_count)]
        if self.max_title_width:
            width_boxes = [min(w, self.max_title_width) for w in width_boxes]
        width_sum = sum(width_boxes)

        # calculated box width are to wide for available widget space:
        if width_sum > width_total:
            # sum the width of tasks shorter than calculated average
            # and calculate a ratio to shrink boxes greater than width_avg
            width_shorter_sum = sum([w for w in width_boxes if w < width_avg])

            ratio = ((width_total - width_shorter_sum) /
                     (width_sum - width_shorter_sum))
            # determine new box widths by shrinking boxes greater than avg
            width_boxes = [(w if w < width_avg else w * ratio)
                           for w in width_boxes]

        return zip(windows, icons, names, width_boxes)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        if self.icon_size is None:
            self.icon_size = self.bar.height - 2 * (self.borderwidth +
                                                    self.margin_y)

        if self.fontsize is None:
            calc = self.bar.height - self.margin_y * 2 - \
                self.borderwidth * 2 - self.padding_y * 2
            self.fontsize = max(calc, 1)
        self.layout = self.drawer.textlayout(
            "",
            "ffffff",
            self.font,
            self.fontsize,
            self.fontshadow,
            wrap=False
        )
        self.setup_hooks()

    def update(self, window=None):
        if not window or window in self.windows:
            self.bar.draw()

    def remove_icon_cache(self, window):
        wid = window.window.wid
        if wid in self._icons_cache:
            self._icons_cache.pop(wid)

    def invalidate_cache(self, window):
        self.remove_icon_cache(window)
        self.update(window)

    def setup_hooks(self):
        hook.subscribe.client_name_updated(self.update)
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

    def drawbox(self, offset, text, bordercolor, textcolor,
                width=None, rounded=False, block=False, icon=None):
        self.drawtext(text, textcolor, width)

        icon_padding = (self.icon_size + self.padding_x) if icon else 0
        padding_x = [self.padding_x + icon_padding, self.padding_x]

        framed = self.layout.framed(
            self.borderwidth,
            bordercolor,
            padding_x,
            self.padding_y
        )
        if block:
            framed.draw_fill(offset, self.margin_y, rounded)
        else:
            framed.draw(offset, self.margin_y, rounded)

        if icon:
            self.draw_icon(icon, offset)

    def get_clicked(self, x, y):
        box_start = self.margin_x
        for box_end, win in zip(self._box_end_positions, self.windows):
            if box_start <= x <= box_end:
                return win
            else:
                box_start = box_end + self.spacing
        # not found any , return None
        return None

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
        elif window:
            window.toggle_minimize()

    def get_window_icon(self, window):
        if not window.icons:
            return None

        cache = self._icons_cache.get(window.window.wid)
        if cache:
            return cache

        icons = sorted(
            iter(window.icons.items()),
            key=lambda x: abs(self.icon_size - int(x[0].split("x")[0]))
        )
        icon = icons[0]
        width, height = map(int, icon[0].split("x"))

        img = cairocffi.ImageSurface.create_for_data(
            icon[1],
            cairocffi.FORMAT_ARGB32,
            width,
            height
        )

        surface = cairocffi.SurfacePattern(img)

        scaler = cairocffi.Matrix()

        if height != self.icon_size:
            sp = height / self.icon_size
            height = self.icon_size
            width /= sp
            scaler.scale(sp, sp)
        surface.set_matrix(scaler)
        self._icons_cache[window.window.wid] = surface
        return surface

    def draw_icon(self, surface, offset):
        if not surface:
            return

        x = offset + self.borderwidth + self.padding_x
        y = self.padding_y + self.borderwidth

        self.drawer.ctx.save()
        self.drawer.ctx.translate(x, y)
        self.drawer.ctx.set_source(surface)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        offset = self.margin_x

        self._box_end_positions = []
        for w, icon, task, bw in self.calc_box_widths():
            self._box_end_positions.append(offset + bw)

            if w.urgent:
                border = self.urgent_border
                text_color = border
            elif w is w.group.currentWindow:
                border = self.border
                text_color = border
            else:
                border = self.unfocused_border or (self.background or
                                                   self.bar.background)
                text_color = self.foreground

            if self.highlight_method == 'text':
                border = self.bar.background
            else:
                text_color = self.foreground

            textwidth = (bw - 2 * self.padding_x -
                         ((self.icon_size + self.padding_x) if icon else 0))
            self.drawbox(
                offset,
                task,
                border,
                text_color,
                rounded=self.rounded,
                block=(self.highlight_method == 'block'),
                width=textwidth,
                icon=icon,
            )
            offset += (bw + self.spacing)

        self.drawer.draw(offsetx=self.offset, width=self.width)
