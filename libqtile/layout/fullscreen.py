# Copyright (c) 2023, Jeroen Wijenbergh.
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
from libqtile.backend.base import WindowStates

if TYPE_CHECKING:
    from libqtile.backend.base import Window
    from libqtile.config import ScreenRect


class Fullscreen(_SimpleLayoutBase):
    """Fullscreen layout

    A simple layout that only displays one window at a time, filling the
    entire screen. This is used internally for fullscreen windows
    but can also be used as a dedicated layout.
    """

    defaults = [
        ("border", "#0000ff", "Border colour(s) for the window"),
        ("border_width", 0, "Border width."),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self._manages_win_state = WindowStates.FULLSCREEN
        self.add_defaults(Fullscreen.defaults)

    def add_client(self, client: Window) -> None:  # type: ignore[override]
        return super().add_client(client, 1)

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        if client is self.clients.current_client:
            client.place(
                screen_rect.x,
                screen_rect.y,
                screen_rect.width - self.border_width * 2,
                screen_rect.height - self.border_width * 2,
                self.border_width,
                self.border,
                above=True,
            )
            client.unhide()
        else:
            client.hide()

    @expose_command("previous")
    def up(self):
        _SimpleLayoutBase.previous(self)

    @expose_command("next")
    def down(self):
        _SimpleLayoutBase.next(self)
