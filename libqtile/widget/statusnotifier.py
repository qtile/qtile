# Copyright (c) 2021 elParaguayo
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
from typing import TYPE_CHECKING

from libqtile import bar
from libqtile.widget import base
from libqtile.widget.helpers.status_notifier import has_xdg, host

if TYPE_CHECKING:
    from libqtile.widget.helpers.status_notifier import StatusNotifierItem


class StatusNotifier(base._Widget):
    """
    A 'system tray' widget using the freedesktop StatusNotifierItem
    specification.

    As per the specification, app icons are first retrieved from the
    user's current theme. If this is not available then the app may
    provide its own icon. In order to use this functionality, users
    are recommended to install the `pyxdg <https://pypi.org/project/pyxdg/>`__
    module to support retrieving icons from the selected theme.
    If the icon specified by StatusNotifierItem can not be found in
    the user's current theme and no other icons are provided by the
    app, a fallback icon is used.

    Left-clicking an icon will trigger an activate event.

    .. note::

        Context menus are not currently supported by the official widget.
        However, a modded version of the widget which provides basic menu
        support is available from elParaguayo's `qtile-extras
        <https://github.com/elParaguayo/qtile-extras>`_ repo.
    """

    orientations = base.ORIENTATION_BOTH

    defaults = [
        ("icon_size", 16, "Icon width"),
        ("icon_theme", None, "Name of theme to use for app icons"),
        ("padding", 3, "Padding between icons"),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(StatusNotifier.defaults)
        self.add_callbacks(
            {
                "Button1": self.activate,
            }
        )
        self.selected_item: StatusNotifierItem | None = None

    @property
    def available_icons(self):
        return [item for item in host.items if item.has_icons]

    def calculate_length(self):
        if not host.items:
            return 0

        return len(self.available_icons) * (self.icon_size + self.padding) + self.padding

    def _configure(self, qtile, bar):
        if has_xdg and self.icon_theme:
            host.icon_theme = self.icon_theme

        # This is called last as it starts timers including _config_async.
        base._Widget._configure(self, qtile, bar)

    def draw_callback(self, x=None):
        self.bar.draw()

    async def _config_async(self):
        await host.start(
            on_item_added=self.draw_callback,
            on_item_removed=self.draw_callback,
            on_icon_changed=self.draw_callback,
        )

    def find_icon_at_pos(self, x, y):
        """returns StatusNotifierItem object for icon in given position"""
        offset = self.padding
        val = x if self.bar.horizontal else y

        if val < offset:
            return None

        for icon in self.available_icons:
            offset += self.icon_size
            if val < offset:
                return icon
            offset += self.padding

        return None

    def button_press(self, x, y, button):
        icon = self.find_icon_at_pos(x, y)
        self.selected_item = icon if icon else None

        name = f"Button{button}"
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name]()

    def _draw_icon(self, icon, x, y):
        self.drawer.ctx.set_source_surface(icon, x, y)
        self.drawer.ctx.paint()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        xoffset = self.padding
        yoffset = (self.bar.size - self.icon_size) // 2

        for item in self.available_icons:
            icon = item.get_icon(self.icon_size)
            if self.bar.horizontal:
                self._draw_icon(icon, xoffset, yoffset)
            else:
                self._draw_icon(icon, yoffset, xoffset)
            xoffset += self.icon_size + self.padding

        self.draw_at_default_position()

    def activate(self):
        """Primary action when clicking on an icon"""
        if not self.selected_item:
            return
        self.selected_item.activate()

    def finalize(self):
        host.unregister_callbacks(
            on_item_added=self.draw_callback,
            on_item_removed=self.draw_callback,
            on_icon_changed=self.draw_callback,
        )
        base._Widget.finalize(self)
