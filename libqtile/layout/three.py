import math

from libqtile.layout.base import _SimpleLayoutBase


class ThreeCol(_SimpleLayoutBase):
    defaults = [
        ("border_focus", "#ff0000", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        ("border_width", 2, "Border width."),
        ("single_border_width", None, "Border width for single window"),
        ("single_margin", None, "Margin size for single window"),
        ("margin", 0, "Margin of the layout"),
        (
            "ratio",
            0.5,
            "The percent of the screen-space the master pane should occupy by default.",
        ),
        (
            "new_client_position",
            "after_current",
            "Place new windows: "
            " after_current - after the active window."
            " before_current - before the active window,"
            " top - at the top of the stack,"
            " bottom - at the bottom of the stack,",
        ),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(ThreeCol.defaults)
        if self.single_border_width is None:
            self.single_border_width = self.border_width
        if self.single_margin is None:
            self.single_margin = self.margin
        self.screen_rect = None

    cmd_next = _SimpleLayoutBase.next
    cmd_previous = _SimpleLayoutBase.previous

    def add(self, client, offset_to_current=0, client_position=None):
        """Add client to layout"""
        if client_position is None:
            client_position = self.new_client_position
        self.clients.add(client, offset_to_current, client_position)

    def remove(self, client):
        """Remove client from layout"""
        return self.clients.remove(client)

    def configure(self, client, screen_rect):
        self.screen_rect = screen_rect

        # if client not in this layout
        if not self.clients or client not in self.clients:
            client.hide()
            return

        # determine focus border-color
        if client.has_focus:
            border_color = self.border_focus
        else:
            border_color = self.border_normal

        # helpers
        index = self.clients.index(client)
        client_count = len(self.clients)

        # handle single window as 'Full' with custom borders
        if client_count == 1:
            border_width = self.single_border_width
            margin = self.single_margin

            x = 0
            y = 0
            width = self.screen_rect.width
            height = self.screen_rect.height
        else:
            border_width = self.border_width
            margin = [
                self.margin if index < 3 else 0,
                2 * self.border_width,
                self.margin + 2 * self.border_width,
                self.margin,
            ]

            # divide screen area vertically into 2 or 3 columns
            width_main = int(self.screen_rect.width * self.ratio)
            if client_count == 2:
                width_shared = int(self.screen_rect.width - width_main)
            else:
                width_shared = int((self.screen_rect.width - width_main) / 2)

            # handle main window
            if index == 0:
                x = width_shared if client_count > 2 else 0
                y = 0
                width = width_main
                height = self.screen_rect.height

            # handle children
            else:
                # determine x position in 2 or 3 col view
                if client_count == 2:
                    x = width_main
                elif index % 2 == 1:
                    x = width_main + width_shared
                else:
                    x = 0

                width = width_shared

                # compute height of children on both sides
                if index % 2 == 0:
                    # left side
                    height = int(
                        self.screen_rect.height / (math.floor((client_count - 1) / 2.0))
                    )
                else:
                    # right side
                    height = int(
                        self.screen_rect.height / (math.floor(client_count / 2.0))
                    )
                # position of children depending on height
                y = int(height * math.floor((index - 1) / 2.0))

        # place the window at the computed position
        client.place(
            self.screen_rect.x + x,
            self.screen_rect.y + y,
            width - 2 * border_width,
            height - 2 * border_width,
            border_width,
            border_color,
            margin=margin,
        )
        client.unhide()
