# Copyright (c) 2020 elParaguayo
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

from collections import namedtuple

from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base

BoxedWidget = namedtuple("BoxedWidget", ["widget", "draw"])


def _no_draw(*args, **kwargs):
    pass


class WidgetBox(base._Widget):
    """A widget to declutter your bar.

    WidgetBox is a widget that hides widgets by default but shows them when
    the box is opened.

    Widgets that are hidden will still update etc. as if they were on the main
    bar.

    Button clicks are passed to widgets when they are visible so callbacks will
    work.

    Widgets in the box also remain accessible via command interfaces.

    Widgets can only be added to the box via the configuration file. The widget
    is configured by adding widgets to the "widgets" parameter as follows::

        widget.WidgetBox(widgets=[
            widget.TextBox(text="This widget is in the box"),
            widget.Memory()
            ]
        ),
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            "font",
            "sans",
            "Text font"
        ),
        (
            "fontsize",
            None,
            "Font pixel size. Calculated if None."
        ),
        (
            "fontshadow",
            None,
            "font shadow color, default is None(no shadow)"
        ),
        (
            "foreground",
            "#ffffff",
            "Foreground colour."
        ),
        (
            "close_button_location",
            "left",
            "Location of close button when box open ('left' or 'right')"
        ),
        (
            "text_closed",
            "[<]",
            "Text when box is closed"
        ),
        (
            "text_open",
            "[>]",
            "Text when box is open"
        ),
    ]

    def __init__(self, widgets=list(), **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(WidgetBox.defaults)
        self.box_is_open = False
        self._widgets = widgets
        self.add_callbacks({"Button1": self.cmd_toggle})

        if self.close_button_location not in ["left", "right"]:
            val = self.close_button_location
            msg = "Invalid value for 'close_button_location': {}".format(val)
            logger.warning(msg)
            self.close_button_location = "left"

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.layout = self.drawer.textlayout(
            self.text_closed,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=False,
        )

        for idx, w in enumerate(self._widgets):
            if w.configured:
                w = w.create_mirror()
                self._widgets[idx] = w
            self.qtile.register_widget(w)
            w._configure(self.qtile, self.bar)

            # In case the widget is mirrored, we need to draw it once so the
            # mirror can copy the surface but draw it off screen
            w.offsetx = self.bar.width
            self.qtile.call_soon(w.draw)

        # We need to stop hidden widgets from drawing while hidden
        # (e.g. draw could be triggered by a timer) so we take a reference to
        # the widget's drawer.draw method
        self.widgets = [BoxedWidget(w, w.drawer.draw) for w in self._widgets]

        # # Overwrite the current drawer.draw method with a no-op
        for w in self.widgets:
            w.widget.drawer.draw = _no_draw

    def calculate_length(self):
        return self.layout.width

    def set_box_label(self):
        self.layout.text = (self.text_open if self.box_is_open
                            else self.text_closed)

    def toggle_widgets(self):
        for item in self.widgets:
            try:
                self.bar.widgets.remove(item.widget)
                # Override drawer.drawer with a no-op
                item.widget.drawer.draw = _no_draw
            except ValueError:
                continue

        index = self.bar.widgets.index(self)

        if self.close_button_location == "left":
            index += 1

        if self.box_is_open:

            # Need to reverse list as widgets get added in front of eachother.
            for item in self.widgets[::-1]:
                # Restore the original drawer.draw method
                item.widget.drawer.draw = item.draw
                self.bar.widgets.insert(index, item.widget)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        self.layout.draw(0,
                         int(self.bar.height / 2.0 -
                             self.layout.height / 2.0) + 1)

        self.drawer.draw(offsetx=self.offsetx, width=self.width)

    def button_press(self, x, y, button):
        name = "Button{}".format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name]()

    def cmd_toggle(self):
        """Toggle box state"""
        self.box_is_open = not self.box_is_open
        self.toggle_widgets()
        self.set_box_label()
        self.bar.draw()
