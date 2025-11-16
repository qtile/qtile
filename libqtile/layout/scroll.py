from typing import cast

from libqtile.backend.base import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout import base


class Scroll(base.Layout):
    """
    Scrollable 2D tiling system.

    Horizontal scrolling plus vertical stacking — with predictable, stable behavior.
    """

    defaults = [
        ("border_width", 5, "Window border width"),
        ("border_focus", "ff0000", "Window focused border colour"),
        ("border_normal", "333333", "Window normal border colour"),
        ("margin_focused", 5, "Margin width for focused windows"),
        ("margin_unfocused", 5, "Margin width for unfocused windows"),
    ]

    def __init__(self, **config):
        base.Layout.__init__(self, **config)
        self.add_defaults(Scroll.defaults)
        self.clients = []
        self.current_client = None
        self.offset_x = 0

    def clone(self, group):
        """Create a new instance for each workspace/group."""
        c = base.Layout.clone(self, group)
        c.clients = []
        c.current_client = None
        c.offset_x = 0
        return c

    # --------------------------
    # Core layout logic
    # --------------------------
    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        try:
            index = self.clients.index(client)
        except ValueError:
            return

        border = cast(int, self.border_width)
        # Each window takes half the screen width (two per view)
        column_width = screen_rect.width // 2
        x = screen_rect.x + index * column_width - self.offset_x
        y = screen_rect.y
        w = column_width
        h = screen_rect.height

        # Hide windows far outside the viewport
        if x + w < screen_rect.x - w or x > screen_rect.x + screen_rect.width + w:
            client.hide()
            return

        if client.has_focus:
            px = self.border_focus
        else:
            px = self.border_normal

        client.unhide()
        margin = self.margin_focused if client is self.current_client else self.margin_unfocused
        client.place(
            x,
            y,
            w - border * 2,
            h - border * 2,
            border,
            px,
            margin=[margin] * 4,
        )

    def add_client(self, client: Window) -> None:
        # Assumes self.clients is simple list
        self.clients.append(client)
        self.current_client = client

    def remove(self, client: Window) -> Window | None:
        # Assumes self.clients is a simple list
        # Client already removed so ignore this
        if client not in self.clients:
            return None
        # Client is only window in the list
        elif len(self.clients) == 1:
            self.clients.remove(client)
            self.current_client = None
            # There are no other windows so return None
            return None
        else:
            # Find position of client in our list
            index = self.clients.index(client)
            # Remove client
            self.clients.remove(client)
            # Ensure the index value is not greater than list size
            # i.e. if we closed the last window in the list, we need to return
            # the first one (index 0).
            index %= len(self.clients)
            next_client = self.clients[index]
            self.current_client = next_client
            return next_client

    def focus_first(self) -> Window | None:
        if not self.clients:
            return None

        return self.clients[0]

    def focus_last(self) -> Window | None:
        if not self.clients:
            return None

        return self.clients[-1]

    def focus_next(self, win: Window) -> Window | None:
        try:
            return self.clients[self.clients.index(win) + 1]
        except IndexError:
            return None

    def focus_previous(self, win: Window) -> Window | None:
        if not self.clients or self.clients.index(win) == 0:
            return None

        try:
            return self.clients[self.clients.index(win) - 1]
        except IndexError:
            return None

    def next(self) -> None:
        if self.current_client is None:
            return
        # Get the next client or, if at the end of the list, get the first
        client = self.focus_next(self.current_client) or self.focus_first()
        self.group.focus(client, True)

    def previous(self) -> None:
        if self.current_client is None:
            return
        # Get the previous client or, if at the end of the list, get the last
        client = self.focus_previous(self.current_client) or self.focus_last()
        self.group.focus(client, True)

    # --------------------------
    # Scrolling behavior
    # --------------------------
    @expose_command()
    def scroll_right(self):
        """Focus next client; scroll if it's beyond current visible pair."""
        if not self.clients or not self.current_client:
            return

        next_client = self.focus_next(self.current_client)
        if not next_client:
            return

        next_index = self.clients.index(next_client)

        screen = getattr(self.group, "screen", None)
        if not screen:
            return

        col_w = screen.width // 2
        left_visible = int(self.offset_x // col_w)
        right_visible = left_visible + 1

        # If next client is already in visible pair -> no scroll
        if next_index in (left_visible, right_visible):
            self.current_client = next_client
            self.group.focus(next_client, True)
            self.group.layout_all()
            return

        # Otherwise scroll one column
        self.offset_x = (next_index - 1) * col_w
        self.current_client = next_client
        self.group.focus(next_client, True)
        self.group.layout_all()

    @expose_command()
    def scroll_left(self):
        """Focus previous client; scroll if it's beyond current visible pair."""
        if not self.clients or not self.current_client:
            return

        prev_client = self.focus_previous(self.current_client)
        if not prev_client:
            return

        prev_index = self.clients.index(prev_client)

        screen = getattr(self.group, "screen", None)
        if not screen:
            return

        col_w = screen.width // 2
        left_visible = int(self.offset_x // col_w)
        right_visible = left_visible + 1

        # If previous client is already visible -> no scroll
        if prev_index in (left_visible, right_visible):
            self.current_client = prev_client
            self.group.focus(prev_client, True)
            self.group.layout_all()
            return

        # Otherwise scroll one column left
        self.offset_x = prev_index * col_w
        self.current_client = prev_client
        self.group.focus(prev_client, True)
        self.group.layout_all()
