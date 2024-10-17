# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# Copyright (c) 2017, Dirk Hartmann.
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
from libqtile.layout.base import _SimpleLayoutBase

if TYPE_CHECKING:
    from libqtile.backend.base import Window
    from libqtile.config import ScreenRect


class Max(_SimpleLayoutBase):
    """Maximized layout

    A simple layout that only displays one window at a time, filling the
    screen_rect. This is suitable for use on laptops and other devices with
    small screens. Conceptually, the windows are managed as a stack, with
    commands to switch to next and previous windows in the stack.
    """

    defaults = [
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])"),
        ("border_focus", "#0000ff", "Border colour(s) for the window when focused"),
        ("border_normal", "#000000", "Border colour(s) for the window when not focused"),
        ("border_width", 0, "Border width."),
        ("only_focused", True, "Only draw the focused window"),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Max.defaults)

    def add_client(self, client: Window) -> None:  # type: ignore[override]
        return super().add_client(client, 1)

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        if not self.only_focused or (self.clients and client is self.clients.current_client):
            client.place(
                screen_rect.x,
                screen_rect.y,
                screen_rect.width - self.border_width * 2,
                screen_rect.height - self.border_width * 2,
                self.border_width,
                self.border_focus if client.has_focus else self.border_normal,
                margin=self.margin,
            )
            client.unhide()
            if (
                not self.only_focused
                and self.clients
                and client is self.clients.current_client
                and len(self.clients) > 1
            ):
                client.move_to_top()
        else:
            client.hide()

    @expose_command("previous")
    def up(self):
        _SimpleLayoutBase.previous(self)

    @expose_command("next")
    def down(self):
        _SimpleLayoutBase.next(self)
