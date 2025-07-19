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
from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.pangocffi import markup_escape_text
from libqtile.widget import Systray, base

if TYPE_CHECKING:
    from typing import Any


class WidgetBox(base._TextBox):
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
    defaults: list[tuple[str, Any, str]] = [
        (
            "close_button_location",
            "left",
            "Location of close button when box open ('left' or 'right')",
        ),
        ("text_closed", "[<]", "Text when box is closed"),
        ("text_open", "[>]", "Text when box is open"),
        ("widgets", list(), "A list of widgets to include in the box"),
        ("start_opened", False, "Spawn the box opened"),
    ]

    def __init__(self, _widgets: list[base._Widget] | None = None, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(WidgetBox.defaults)
        self.box_is_open = False
        self.add_callbacks({"Button1": self.toggle})

        if _widgets:
            logger.warning(
                "The use of a positional argument in WidgetBox is deprecated. "
                "Please update your config to use widgets=[...]."
            )
            self.widgets = _widgets

        self.close_button_location: str
        if self.close_button_location not in ["left", "right"]:
            val = self.close_button_location
            logger.warning("Invalid value for 'close_button_location': %s", val)
            self.close_button_location = "left"

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

        self.text = markup_escape_text(self.text_open if self.box_is_open else self.text_closed)

        if self.configured:
            return

        for idx, w in enumerate(self.widgets):
            if w.configured:
                w = w.create_mirror()
                self.widgets[idx] = w
            self.qtile.register_widget(w)
            w._configure(self.qtile, self.bar)
            w.offsety = self.bar.border_width[0]

            # In case the widget is mirrored, we need to draw it once so the
            # mirror can copy the surface but draw it off screen
            w.offsetx = self.bar.length
            self.qtile.call_soon(w.draw)

            # Setting the configured flag for widgets was moved to Bar._configure so we need to
            # set it here.
            w.configured = True

        # Disable drawing of the widget's contents
        for w in self.widgets:
            w.drawer.disable()

        # We're being cautious: `box_is_open` should never be True here...
        if self.start_opened and not self.box_is_open:
            self.qtile.call_soon(self.toggle)

    def set_box_label(self):
        self.text = markup_escape_text(self.text_open if self.box_is_open else self.text_closed)

    def toggle_widgets(self):
        for widget in self.widgets:
            try:
                self.bar.widgets.remove(widget)
                # Override drawer.drawer with a no-op
                widget.drawer.disable()

                # Systray widget needs some additional steps to hide as the icons
                # are separate _Window instances.
                # Systray unhides icons when it draws so we only need to hide them.
                if isinstance(widget, Systray):
                    for icon in widget.tray_icons:
                        icon.hide()

            except ValueError:
                continue

        index = self.bar.widgets.index(self)

        if self.close_button_location == "left":
            index += 1

        if self.box_is_open:
            # Need to reverse list as widgets get added in front of eachother.
            for widget in self.widgets[::-1]:
                # enable drawing again
                widget.drawer.enable()
                self.bar.widgets.insert(index, widget)

    @expose_command()
    def toggle(self):
        """Toggle box state"""
        self.box_is_open = not self.box_is_open
        self.toggle_widgets()
        self.set_box_label()
        self.bar.draw()

    @expose_command()
    def open(self):
        """Open the widgetbox."""
        if not self.box_is_open:
            self.toggle()

    @expose_command()
    def close(self):
        """Close the widgetbox."""
        if self.box_is_open:
            self.toggle()
