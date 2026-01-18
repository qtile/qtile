from __future__ import annotations

from typing import TYPE_CHECKING

import libqtile
from libqtile.command.base import expose_command
from libqtile.layout.base import _SimpleLayoutBase

if TYPE_CHECKING:
    from libqtile.backend.base import Window
    from libqtile.config import ScreenRect


class Zoomy(_SimpleLayoutBase):
    """A layout with single active windows, and few other previews at the right"""

    defaults = [
        ("columnwidth", 150, "Width of the right column"),
        ("property_name", "ZOOM", "Property to set on zoomed window (X11 only)"),
        ("property_small", "0.1", "Property value to set on zoomed window (X11 only)"),
        ("property_big", "1.0", "Property value to set on normal window (X11 only)"),
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])"),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(Zoomy.defaults)

    def add_client(self, client: Window) -> None:  # type: ignore[override]
        self.clients.append_head(client)

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        left, right = screen_rect.hsplit(screen_rect.width - self.columnwidth)
        if client is self.clients.current_client:
            client.place(
                left.x,
                left.y,
                left.width,
                left.height,
                0,
                None,
                margin=self.margin,
            )
        else:
            h = right.width * left.height // left.width
            client_index = self.clients.index(client)
            focused_index = self.clients.current_index
            offset = client_index - focused_index - 1
            if offset < 0:
                offset += len(self.clients)
            if h * (len(self.clients) - 1) < right.height:
                client.place(
                    right.x,
                    right.y + h * offset,
                    right.width,
                    h,
                    0,
                    None,
                    margin=self.margin,
                )
            else:
                hh = (right.height - h) // (len(self.clients) - 1)
                client.place(
                    right.x,
                    right.y + hh * offset,
                    right.width,
                    h,
                    0,
                    None,
                    margin=self.margin,
                )
        client.unhide()

    def focus(self, win):
        if self.property_name and libqtile.qtile.core.name != "x11":
            self.property_name = ""

        if (
            self.clients.current_client
            and self.property_name
            and self.clients.current_client.window.get_property(self.property_name, "UTF8_STRING")
            is not None
        ):
            self.clients.current_client.window.set_property(
                self.property_name, self.property_small, "UTF8_STRING", format=8
            )
        _SimpleLayoutBase.focus(self, win)
        if self.property_name:
            win.window.set_property(
                self.property_name, self.property_big, "UTF8_STRING", format=8
            )

    @expose_command("down")
    def next(self) -> None:
        _SimpleLayoutBase.next(self)

    @expose_command("up")
    def previous(self) -> None:
        _SimpleLayoutBase.previous(self)
