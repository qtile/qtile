from libqtile.backend.base import Window
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout import base
from libqtile.utils import ColorsType


def flatten(lst):
    for item in lst:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


class Scroll(base.Layout):
    """
    Scrollable 2D tiling system, niri-style.

    Windows are arranged in columns that scroll horizontally. Within a
    column, windows keep a natural height and the column scrolls
    vertically when its windows overflow the screen, rather than always
    shrinking every window to fit.
    """

    border_width: int
    border_focus: ColorsType
    border_normal: ColorsType
    margin: int
    column_width: int | None
    columns_per_screen: int
    center_on_focus: bool
    add_at_focus: bool
    new_window_position: str
    resize_step: int
    default_window_height_ratio: float
    min_column_width: int
    min_window_height: int

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
        ("center_on_focus", True, "Center active column on focus (niri-style)"),
        ("add_at_focus", True, "Insert at focus position"),
        ("new_window_position", "after", "Position of new windows (before/after)"),
        ("resize_step", 50, "Pixels to resize column/window by"),
        (
            "default_window_height_ratio",
            0.5,
            "Fraction of screen height a new window in a column defaults to",
        ),
        ("min_column_width", 100, "Minimum column width in pixels"),
        ("min_window_height", 50, "Minimum window height in pixels"),
    ]

    def __init__(self, **config):
        base.Layout.__init__(self, **config)
        self.add_defaults(Scroll.defaults)
        self.clients: list[list[Window]] = []  # [[win1, win2], [win3]]
        self.client_column_widths: dict[int, int] = {}  # col_idx -> width
        self.client_window_heights: dict[Window, int] = {}  # win -> height
        self.column_offset_y: dict[int, int] = {}  # col_idx -> vertical scroll offset
        self.focused: Window | None = None
        self.focused_column: int = 0
        self.focused_window: int = 0
        self.offset_x: int = 0
        self._last_geometry: dict[Window, tuple] = {}
        self._last_fullscreen: dict[Window, bool] = {}

    def clone(self, group):
        """Create a new instance for each workspace/group."""
        c = base.Layout.clone(self, group)
        assert isinstance(c, Scroll)
        c.clients = []
        c.client_column_widths = {}
        c.client_window_heights = {}
        c.column_offset_y = {}
        c.focused = None
        c.focused_column = 0
        c.focused_window = 0
        c.offset_x = 0
        c._last_geometry = {}
        c._last_fullscreen = {}
        return c

    def _get_window_position(self, client: Window) -> tuple[int, int] | None:
        for i, col in enumerate(self.clients):
            if client in col:
                return i, col.index(client)
        return None

    def _focused_pos(self) -> tuple[int, int] | None:
        """
        Column/window index of the focused window, or None if there's
        nothing focused / nothing laid out.
        """
        if not self.focused or not self.clients:
            return None
        return self._get_window_position(self.focused)

    def _screen_size(self) -> tuple[int, int]:
        assert self.group.screen is not None
        return self.group.screen.width, self.group.screen.height

    def _default_column_width(self, screen_width: int | None = None) -> int:
        if self.column_width is not None:
            return self.column_width
        if screen_width is None:
            screen_width, _ = self._screen_size()
        width: int = screen_width
        return width // self.columns_per_screen

    def _default_window_height(self, screen_height: int | None = None) -> int:
        if screen_height is None:
            _, screen_height = self._screen_size()
        height: int = screen_height
        return int(height * self.default_window_height_ratio)

    def _column_window_height(self, win: Window, screen_rect: ScreenRect) -> int:
        """
        Natural height for a window in a column: explicit override, else a
        default fraction of screen height (niri-style, not forced to fit).
        """
        return self.client_window_heights.get(
            win, self._default_window_height(screen_rect.height)
        )

    def _invalidate_if_fullscreen_changed(self, win: Window) -> None:
        """
        A window's fullscreen state can be changed by code outside this
        layout (core fullscreen toggle), which places it directly and
        bypasses our geometry cache. If that happened, the cache is stale
        relative to the window's actual on-screen geometry, so drop it and
        force a real place() next time this window is laid out.
        """
        was_fullscreen = self._last_fullscreen.get(win, False)
        if win.fullscreen != was_fullscreen:
            self._last_geometry.pop(win, None)
        self._last_fullscreen[win] = win.fullscreen

    def _set_visible(self, win: Window, visible: bool) -> None:
        """
        Show or hide a window.
        """
        win.unhide() if visible else win.hide()

    def focus(self, client: Window) -> None:
        self.focused = client
        pos = self._get_window_position(client)
        if pos:
            self.focused_column, self.focused_window = pos

    def configure(self, client: Window, screen_rect: ScreenRect) -> None:
        self._invalidate_if_fullscreen_changed(client)

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
            self._set_visible(win, True)
            return

        pos = self._get_window_position(client)
        if not self.clients or pos is None:
            self._set_visible(client, False)
            return

        if client.has_focus:
            self.focus(client)

        default_width = self._default_column_width(screen_rect.width)
        self._update_offset_x(default_width, screen_rect)

        current_x = 0
        for i, col in enumerate(self.clients):
            column_width = self.client_column_widths.get(i, default_width)

            if not col:
                current_x += column_width
                continue

            col_x = int(screen_rect.x + current_x - self.offset_x)
            visible = (
                screen_rect.x <= col_x + column_width
                and col_x <= screen_rect.x + screen_rect.width
            )

            if not visible:
                for win in col:
                    self._set_visible(win, False)
            else:
                self._layout_column(i, col, col_x, column_width, screen_rect)

            current_x += column_width

    def _update_offset_x(self, default_width: int, screen_rect: ScreenRect) -> None:
        """
        Recompute horizontal scroll offset so the focused column is
        visible (or centered, if center_on_focus). Clamped so we never
        scroll past the first/last column.
        """
        total_width = sum(
            self.client_column_widths.get(j, default_width) for j in range(len(self.clients))
        )
        max_offset = max(0, total_width - screen_rect.width)

        if not self.clients or self.focused is None:
            self.offset_x = 0
            return

        focused_col_x = sum(
            self.client_column_widths.get(j, default_width) for j in range(self.focused_column)
        )
        focused_col_width = self.client_column_widths.get(self.focused_column, default_width)

        if self.center_on_focus and len(self.clients) > 1:
            offset = focused_col_x - screen_rect.width // 2 + focused_col_width // 2
        else:
            offset = self.offset_x
            if focused_col_x - offset + focused_col_width > screen_rect.width:
                offset = focused_col_x - screen_rect.width + focused_col_width
            elif focused_col_x - offset < 0:
                offset = focused_col_x

        self.offset_x = max(0, min(offset, max_offset))

    def _ensure_column_visible_y(
        self, col_idx: int, col: list[Window], screen_rect: ScreenRect
    ) -> None:
        """
        Adjust column_offset_y so the focused window (if in this column)
        is visible, niri-style vertical scroll-into-view.
        """
        if col_idx != self.focused_column or self.focused_window >= len(col):
            return

        heights = [self._column_window_height(w, screen_rect) for w in col]
        win_y = sum(heights[: self.focused_window])
        win_h = heights[self.focused_window]
        offset_y = self.column_offset_y.get(col_idx, 0)

        if win_y - offset_y < 0:
            offset_y = win_y
        elif win_y - offset_y + win_h > screen_rect.height:
            offset_y = win_y - screen_rect.height + win_h

        self.column_offset_y[col_idx] = max(0, offset_y)

    def _layout_column(
        self,
        col_idx: int,
        col: list[Window],
        col_x: int,
        column_width: int,
        screen_rect: ScreenRect,
    ) -> None:
        self._ensure_column_visible_y(col_idx, col, screen_rect)

        heights = [self._column_window_height(w, screen_rect) for w in col]
        total_height = sum(heights)

        if total_height <= screen_rect.height:
            offset_y = 0
            self.column_offset_y[col_idx] = 0
            extra = screen_rect.height - total_height
            heights = [h + extra // len(col) for h in heights]
        else:
            offset_y = self.column_offset_y.get(col_idx, 0)

        border_width = self.border_width
        cur_y = 0
        for win, win_h in zip(col, heights):
            win_y = int(screen_rect.y + cur_y - offset_y)
            cur_y += win_h

            if win_y + win_h < screen_rect.y or win_y > screen_rect.y + screen_rect.height:
                self._set_visible(win, False)
                continue

            border_color = self.border_focus if win.has_focus else self.border_normal
            geom = (
                col_x,
                win_y,
                int(column_width - 2 * border_width),
                int(win_h - 2 * border_width),
                border_width,
                border_color,
            )
            self._set_visible(win, True)
            if self._last_geometry.get(win) != geom:
                win.place(*geom, margin=self.margin)
                self._last_geometry[win] = geom

    def add_client(self, client: Window) -> None:
        if not self.clients:
            self.clients.append([client])
            self.focused_column = 0
            self.focused_window = 0
        elif self.add_at_focus:
            self.clients[self.focused_column].insert(self.focused_window, client)
        else:
            insert_at = (
                self.focused_column
                if self.new_window_position == "before"
                else self.focused_column + 1
            )
            self.clients.insert(insert_at, [client])
            self.focused_column = insert_at
            self.focused_window = 0

        self.focused = client

    def remove(self, client: Window) -> Window | None:
        pos = self._get_window_position(client)
        if pos is None:
            return None

        self._last_geometry.pop(client, None)
        self._last_fullscreen.pop(client, None)
        self.client_window_heights.pop(client, None)

        col_idx, win_idx = pos
        self.clients[col_idx].pop(win_idx)

        if self.clients[col_idx]:
            self.focused_column = col_idx
        else:
            self.clients.pop(col_idx)
            self.client_column_widths = self._reindex_after_removal(
                self.client_column_widths, col_idx
            )
            self.column_offset_y = self._reindex_after_removal(self.column_offset_y, col_idx)
            self.focused_column = min(col_idx, len(self.clients) - 1)

        if not self.clients:
            self.focused = None
            self.focused_window = 0
            return None

        self.focused_window = min(self.focused_window, len(self.clients[self.focused_column]) - 1)
        self.focused = self.clients[self.focused_column][self.focused_window]
        return self.focused

    @staticmethod
    def _reindex_after_removal(mapping: dict[int, int], removed_idx: int) -> dict[int, int]:
        """
        Shift dict keys down by one for every index past a removed column.
        """
        return {
            (i - 1 if i > removed_idx else i): v for i, v in mapping.items() if i != removed_idx
        }

    def focus_first(self) -> Window | None:
        return self.clients[0][0] if self.clients else None

    def focus_last(self) -> Window | None:
        return self.clients[-1][-1] if self.clients else None

    def focus_next(self, win: Window) -> Window | None:
        pos = self._get_window_position(win)
        if not pos:
            return None
        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            return self.clients[col_idx][win_idx + 1]
        if col_idx < len(self.clients) - 1:
            return self.clients[col_idx + 1][0]
        return None

    def focus_previous(self, win: Window) -> Window | None:
        pos = self._get_window_position(win)
        if not pos:
            return None
        col_idx, win_idx = pos
        if win_idx > 0:
            return self.clients[col_idx][win_idx - 1]
        if col_idx > 0:
            return self.clients[col_idx - 1][-1]
        return None

    def next(self) -> None:
        self.down()

    def previous(self) -> None:
        self.up()

    @expose_command()
    def up(self) -> None:
        """
        Focus previous window in the current column (scrolls into view).
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if win_idx > 0:
            self.focused_window = win_idx - 1
            self.group.focus(self.clients[col_idx][win_idx - 1], True)

    @expose_command()
    def down(self) -> None:
        """
        Focus next window in the current column (scrolls into view).
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            self.focused_window = win_idx + 1
            self.group.focus(self.clients[col_idx][win_idx + 1], True)

    @expose_command()
    def scroll_up(self) -> None:
        """
        Scroll up within the focused column (alias for up).
        """
        self.up()

    @expose_command()
    def scroll_down(self) -> None:
        """
        Scroll down within the focused column (alias for down).
        """
        self.down()

    @expose_command()
    def scroll_left(self) -> None:
        """
        Focus previous column.
        """
        if not self.clients or self.focused_column <= 0:
            return
        self.focused_column -= 1
        self.focused_window = min(self.focused_window, len(self.clients[self.focused_column]) - 1)
        self.group.focus(self.clients[self.focused_column][self.focused_window], True)

    @expose_command()
    def scroll_right(self) -> None:
        """
        Focus next column.
        """
        if not self.clients or self.focused_column >= len(self.clients) - 1:
            return
        self.focused_column += 1
        self.focused_window = min(self.focused_window, len(self.clients[self.focused_column]) - 1)
        self.group.focus(self.clients[self.focused_column][self.focused_window], True)

    @expose_command()
    def left(self) -> None:
        self.scroll_left()

    @expose_command()
    def right(self) -> None:
        self.scroll_right()

    @expose_command()
    def shuffle_up(self) -> None:
        """
        Move focused window up within its column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if win_idx > 0:
            col = self.clients[col_idx]
            col[win_idx], col[win_idx - 1] = col[win_idx - 1], col[win_idx]
            self.focused_window = win_idx - 1
            self.group.layout_all()

    @expose_command()
    def shuffle_down(self) -> None:
        """
        Move focused window down within its column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if win_idx < len(self.clients[col_idx]) - 1:
            col = self.clients[col_idx]
            col[win_idx], col[win_idx + 1] = col[win_idx + 1], col[win_idx]
            self.focused_window = win_idx + 1
            self.group.layout_all()

    @expose_command()
    def shuffle_left(self) -> None:
        """
        Move focused window to the previous column, or break it into a
        new column if already at the leftmost column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos

        if col_idx == 0:
            if len(self.clients[col_idx]) > 1:
                self._break_into_new_column(col_idx, win_idx, before=True)
            return

        win = self.clients[col_idx].pop(win_idx)
        self.clients[col_idx - 1].append(win)
        if not self.clients[col_idx]:
            self.clients.pop(col_idx)
        self.focused_column = col_idx - 1
        self.focused_window = len(self.clients[self.focused_column]) - 1
        self.group.layout_all()

    @expose_command()
    def shuffle_right(self) -> None:
        """
        Move focused window to the next column, or break it into a new
        column if already at the rightmost column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos

        if col_idx == len(self.clients) - 1:
            if len(self.clients[col_idx]) > 1:
                self._break_into_new_column(col_idx, win_idx, before=False)
            return

        win = self.clients[col_idx].pop(win_idx)
        self.clients[col_idx + 1].insert(0, win)
        if self.clients[col_idx]:
            self.focused_column = col_idx + 1
        else:
            self.clients.pop(col_idx)
            self.focused_column = col_idx
        self.focused_window = 0
        self.group.layout_all()

    def _break_into_new_column(self, col_idx: int, win_idx: int, *, before: bool) -> None:
        """
        Pull a window out of a stacked column into a brand new column
        placed immediately before/after it.
        """
        win = self.clients[col_idx].pop(win_idx)
        new_idx = col_idx if before else col_idx + 1
        self.clients.insert(new_idx, [win])
        self.focused_column = new_idx
        self.focused_window = 0
        self.group.layout_all()

    @expose_command()
    def new_column_before(self) -> None:
        """
        Expel focused window into its own column, placed before current.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if len(self.clients[col_idx]) > 1:
            self._break_into_new_column(col_idx, win_idx, before=True)

    @expose_command()
    def new_column_after(self) -> None:
        """
        Expel focused window into its own column, placed after current.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        if len(self.clients[col_idx]) > 1:
            self._break_into_new_column(col_idx, win_idx, before=False)

    @expose_command()
    def new_column_left(self) -> None:
        self.new_column_before()

    @expose_command()
    def new_column_right(self) -> None:
        self.new_column_after()

    @expose_command()
    def grow(self) -> None:
        """
        Increase the width of the focused column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx = pos[0]
        current = self.client_column_widths.get(col_idx, self._default_column_width())
        self.client_column_widths[col_idx] = current + self.resize_step
        self.group.layout_all()

    @expose_command()
    def shrink(self) -> None:
        """
        Decrease the width of the focused column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx = pos[0]
        current = self.client_column_widths.get(col_idx, self._default_column_width())
        self.client_column_widths[col_idx] = max(
            self.min_column_width, current - self.resize_step
        )
        self.group.layout_all()

    @expose_command()
    def grow_window(self) -> None:
        """
        Increase the height of the focused window within its column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        win = self.clients[col_idx][win_idx]
        current = self.client_window_heights.get(win, self._default_window_height())
        self.client_window_heights[win] = current + self.resize_step
        self.group.layout_all()

    @expose_command()
    def shrink_window(self) -> None:
        """
        Decrease the height of the focused window within its column.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx, win_idx = pos
        win = self.clients[col_idx][win_idx]
        current = self.client_window_heights.get(win, self._default_window_height())
        self.client_window_heights[win] = max(self.min_window_height, current - self.resize_step)
        self.group.layout_all()

    @expose_command()
    def normalize(self) -> None:
        """
        Reset the width of the focused column and heights of its windows to default.
        """
        pos = self._focused_pos()
        if pos is None:
            return
        col_idx = pos[0]
        self.client_column_widths.pop(col_idx, None)
        for win in self.clients[col_idx]:
            self.client_window_heights.pop(win, None)
        self.group.layout_all()

    @expose_command()
    def info(self):
        info = super().info()
        info["clients"] = [c.name for c in flatten(self.clients)]
        return info
