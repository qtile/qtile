from libqtile.backend.base import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout import base


def flatten(lst):
    for item in lst:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


class Scroll(base.Layout):
    """
    Scrollable 2D tiling system.

    Horizontal scrolling plus vertical stacking — with predictable, stable behavior.
    """

    defaults = [
        ("border_width", 5, "Window border width"),
        ("border_focus", "ff0000", "Window focused border colour"),
        ("border_normal", "333333", "Window normal border colour"),
        ("margin", 5, "Margin width for windows"),
        (
            "column_width",
            None,
            "Default client column width (None = auto-calculate based on screen)",
        ),
        (
            "columns_per_screen",
            2,
            "Number of client columns to fit on screen when auto-calculating width",
        ),
        ("center_on_focus", False, "Center active column on focus"),
        ("add_at_focus", True, "Insert at focus position"),
        ("new_window_position", "after", "Position of new windows (before/after)"),
        ("resize_step", 50, "Pixels to resize column width by"),
    ]

    def __init__(self, **config):
        base.Layout.__init__(self, **config)
        self.add_defaults(Scroll.defaults)
        self.clients = []  # List of lists, e.g. [[win1, win2], [win3]]
        self.client_column_widths = {}  # Dict mapping column index to custom width
        self.focused = None
        self.focused_column = 0
        self.focused_window = 0
        self.offset_x = 0

    def clone(self, group):
        """Create a new instance for each workspace/group."""
        c = base.Layout.clone(self, group)
        c.clients = []
        c.client_column_widths = {}
        c.focused = None
        c.focused_column = 0
        c.focused_window = 0
        c.offset_x = 0
        return c

    # --------------------------
    # Core layout logic
    # --------------------------
    def focus(self, client: Window) -> None:
        self.focused = client
        pos = self._get_window_position(client)
        if pos:
            self.focused_column, self.focused_window = pos

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        if len(self.clients) == 1 and len(self.clients[0]) == 1:
            win = self.clients[0][0]
            win.place(
                screen_rect.x,
                screen_rect.y,
                screen_rect.width - self.border_width * 2,
                screen_rect.height - self.border_width * 2,
                self.border_width,
                self.border_focus if win.has_focus else self.border_normal,
                margin=self.margin,
            )
            win.unhide()
            return

        pos = self._get_window_position(client)
        if not self.clients or pos is None:
            client.hide()
            return

        if client.has_focus:
            self.focus(client)

        # Calculate default column width
        if self.column_width is None:
            default_column_width = screen_rect.width // self.columns_per_screen
        else:
            default_column_width = self.column_width

        if self.center_on_focus and self.focused is not None and len(self.clients) > 1:
            # Center the focused column in the screen (only if there are multiple clients)
            focused_col_x = sum(
                self.client_column_widths.get(j, default_column_width)
                for j in range(self.focused_column)
            )
            screen_center_x = screen_rect.width // 2
            focused_col_width = self.client_column_widths.get(
                self.focused_column, default_column_width
            )
            self.offset_x = focused_col_x - screen_center_x + focused_col_width // 2
        else:
            # Ensure focused column is visible by scrolling if needed
            if self.focused is not None and len(self.clients) > 0:
                focused_col_x = sum(
                    self.client_column_widths.get(j, default_column_width)
                    for j in range(self.focused_column)
                )
                focused_col_width = self.client_column_widths.get(
                    self.focused_column, default_column_width
                )
                # If focused column is off-screen to the right
                if focused_col_x - self.offset_x + focused_col_width > screen_rect.width:
                    self.offset_x = focused_col_x - screen_rect.width + focused_col_width
                # If focused column is off-screen to the left
                elif focused_col_x - self.offset_x < 0:
                    self.offset_x = focused_col_x
            else:
                self.offset_x = 0

        current_x = 0
        for i, col in enumerate(self.clients):
            column_width = self.client_column_widths.get(i, default_column_width)

            if not col:
                current_x += column_width
                continue

            col_x = int(screen_rect.x + current_x - self.offset_x)
            win_height = int(screen_rect.height // len(col))

            # Check if column is visible
            if col_x + column_width < screen_rect.x or col_x > screen_rect.x + screen_rect.width:
                for win in col:
                    win.hide()
                current_x += column_width
                continue

            for j, win in enumerate(col):
                win_y = int(screen_rect.y + j * win_height)
                border_width = self.border_width
                border_color = self.border_focus if win.has_focus else self.border_normal

                win.unhide()
                win.place(
                    col_x,
                    win_y,
                    int(column_width - 2 * border_width),
                    int(win_height - 2 * border_width),
                    border_width,
                    border_color,
                    margin=self.margin,
                )

            current_x += column_width

    def _get_window_position(self, client: Window) -> tuple[int, int] | None:
        """Finds the position of a client in the column layout."""
        for i, col in enumerate(self.clients):
            try:
                j = col.index(client)
                return i, j
            except ValueError:
                pass
        return None

    def add_client(self, client: Window) -> None:
        """Add a new client window to the layout."""
        if not self.clients:
            # First window - create first column
            self.clients.append([client])
            self.focused_column = 0
            self.focused_window = 0
        elif self.add_at_focus:
            # Add to current column (vertical split)
            self.clients[self.focused_column].insert(self.focused_window, client)
        else:
            # Add as new column (horizontal split)
            if self.new_window_position == "before":
                self.clients.insert(self.focused_column, [client])
                # Don't change focused_column since we inserted before
            else:
                # Insert after current column
                self.clients.insert(self.focused_column + 1, [client])
                self.focused_column += 1
            self.focused_window = 0

        self.focused = client

    def remove(self, client: Window) -> Window | None:
        pos = self._get_window_position(client)
        if pos is None:
            return None

        col_idx, win_idx = pos
        self.clients[col_idx].pop(win_idx)

        # Remove empty column
        if not self.clients[col_idx]:
            self.clients.pop(col_idx)
            # Update column widths dict - shift all indices after removed column
            new_widths = {}
            for i, width in self.client_column_widths.items():
                if i < col_idx:
                    new_widths[i] = width
                elif i > col_idx:
                    new_widths[i - 1] = width
            self.client_column_widths = new_widths

            if not self.clients:
                self.focused = None
                self.focused_column = 0
                self.focused_window = 0
                return None
            # Adjust focused_column if needed
            if self.focused_column >= len(self.clients):
                self.focused_column = len(self.clients) - 1

        # Adjust focused_window if needed
        if self.focused_column < len(self.clients):
            if self.focused_window >= len(self.clients[self.focused_column]):
                self.focused_window = len(self.clients[self.focused_column]) - 1
            self.focused = self.clients[self.focused_column][self.focused_window]
        else:
            self.focused = None

        return self.focused

    def focus_first(self) -> Window | None:
        if not self.clients:
            return None
        return self.clients[0][0]

    def focus_last(self) -> Window | None:
        if not self.clients:
            return None
        return self.clients[-1][-1]

    def focus_next(self, win: Window) -> Window | None:
        pos = self._get_window_position(win)
        if not pos:
            return None

        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            return self.clients[col_idx][win_idx + 1]
        elif col_idx < len(self.clients) - 1:
            return self.clients[col_idx + 1][0]
        else:
            return None

    def focus_previous(self, win: Window) -> Window | None:
        pos = self._get_window_position(win)
        if not pos:
            return None

        col_idx, win_idx = pos
        if win_idx > 0:
            return self.clients[col_idx][win_idx - 1]
        elif col_idx > 0:
            return self.clients[col_idx - 1][-1]
        else:
            return None

    @expose_command()
    def up(self) -> None:
        """Focus previous window in the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if win_idx > 0:
            self.focused_window = win_idx - 1
            self.group.focus(self.clients[col_idx][win_idx - 1], True)

    @expose_command()
    def down(self) -> None:
        """Focus next window in the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            self.focused_window = win_idx + 1
            self.group.focus(self.clients[col_idx][win_idx + 1], True)

    def next(self) -> None:
        self.down()

    def previous(self) -> None:
        self.up()

    @expose_command()
    def shuffle_up(self) -> None:
        """Move focused window up in the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if win_idx > 0:
            self.clients[col_idx][win_idx], self.clients[col_idx][win_idx - 1] = (
                self.clients[col_idx][win_idx - 1],
                self.clients[col_idx][win_idx],
            )
            self.focused_window = win_idx - 1
            self.group.layout_all()

    @expose_command()
    def shuffle_down(self) -> None:
        """Move focused window down in the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            self.clients[col_idx][win_idx], self.clients[col_idx][win_idx + 1] = (
                self.clients[col_idx][win_idx + 1],
                self.clients[col_idx][win_idx],
            )
            self.focused_window = win_idx + 1
            self.group.layout_all()

    @expose_command()
    def shuffle_left(self):
        """Move focused window to the previous column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if col_idx > 0:
            win = self.clients[col_idx].pop(win_idx)
            self.clients[col_idx - 1].append(win)
            if not self.clients[col_idx]:
                self.clients.pop(col_idx)
                self.focused_column = col_idx - 1
            else:
                self.focused_column -= 1
            self.focused_window = len(self.clients[self.focused_column]) - 1
            self.group.layout_all()

    @expose_command()
    def shuffle_right(self):
        """Move focused window to the next column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if col_idx < len(self.clients) - 1:
            win = self.clients[col_idx].pop(win_idx)
            self.clients[col_idx + 1].insert(0, win)
            if not self.clients[col_idx]:
                self.clients.pop(col_idx)
            else:
                self.focused_column += 1
            self.focused_window = 0
            self.group.layout_all()

    @expose_command()
    def new_column_before(self):
        """Create a new column with the focused window, and place it before the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if len(self.clients[col_idx]) > 1:
            win = self.clients[col_idx].pop(win_idx)
            self.clients.insert(col_idx, [win])
            self.focused_column = col_idx
            self.focused_window = 0
            self.group.layout_all()

    @expose_command()
    def new_column_after(self):
        """Create a new column with the focused window, and place it after the current column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx, win_idx = pos
        if len(self.clients[col_idx]) > 1:
            win = self.clients[col_idx].pop(win_idx)
            self.clients.insert(col_idx + 1, [win])
            self.focused_column = col_idx + 1
            self.focused_window = 0
            self.group.layout_all()

    @expose_command()
    def new_column_left(self):
        """Create a new column with the focused window, and place it to the left of the current column."""
        self.new_column_before()

    @expose_command()
    def new_column_right(self):
        """Create a new column with the focused window, and place it to the right of the current column."""
        self.new_column_after()

    # --------------------------
    # Scrolling behavior
    # --------------------------
    @expose_command()
    def scroll_right(self):
        """Focus next column."""
        if not self.clients:
            return
        if self.focused_column < len(self.clients) - 1:
            self.focused_column += 1
            self.focused_window = 0
            self.group.focus(self.clients[self.focused_column][0], True)

    @expose_command()
    def scroll_left(self):
        """Focus previous column."""
        if not self.clients:
            return
        if self.focused_column > 0:
            self.focused_column -= 1
            self.focused_window = 0
            self.group.focus(self.clients[self.focused_column][0], True)

    @expose_command()
    def grow_width(self):
        """Increase the width of the focused column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx = pos[0]
        # Get current width or default
        if self.column_width is None:
            default_width = self.group.screen.width // self.columns_per_screen
        else:
            default_width = self.column_width

        current_width = self.client_column_widths.get(col_idx, default_width)
        self.client_column_widths[col_idx] = current_width + self.resize_step
        self.group.layout_all()

    @expose_command()
    def shrink_width(self):
        """Decrease the width of the focused column."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx = pos[0]
        # Get current width or default
        if self.column_width is None:
            default_width = self.group.screen.width // self.columns_per_screen
        else:
            default_width = self.column_width

        current_width = self.client_column_widths.get(col_idx, default_width)
        # Minimum width of 100 pixels
        new_width = max(100, current_width - self.resize_step)
        self.client_column_widths[col_idx] = new_width
        self.group.layout_all()

    @expose_command()
    def reset_width(self):
        """Reset the width of the focused column to default."""
        if not self.focused or not self.clients:
            return

        pos = self._get_window_position(self.focused)
        if not pos:
            return

        col_idx = pos[0]
        if col_idx in self.client_column_widths:
            del self.client_column_widths[col_idx]
            self.group.layout_all()

    @expose_command()
    def info(self):
        info = super().info()
        info["clients"] = [c.name for c in flatten(self.clients)]
        return info
