import math

from base import Layout


class Matrix(Layout):
    """
        This layout divides the screen into a matrix of equally sized cells
        and places one window in each cell. The number of columns is
        configurable and can also be changed interactively.
    """
    defaults = [
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("name", "matrix", "Name of this layout."),
    ]

    def __init__(self, columns=2, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Matrix.defaults)
        self.current_window = None
        self.columns = columns
        self.windows = []

    def info(self):
        d = Layout.info(self)
        d["rows"] = [[win.name for win in self.get_row(i)]
                     for i in xrange(self.get_num_rows())]
        d["current_window"] = self.current_window
        return d

    def clone(self, group):
        c = Layout.clone(self, group)
        c.windows = []
        return c

    def get_current_window(self):
        c, r = self.current_window
        return self.windows[r * self.columns + c]

    def get_num_rows(self):
        return int(math.ceil(float(len(self.windows)) / self.columns))

    def get_row(self, row):
        assert row < self.get_num_rows()
        return self.windows[row * self.columns:
                            row * self.columns + self.columns]

    def get_column(self, column):
        assert column < self.columns
        return [self.windows[i] for i in xrange(column, len(self.windows),
                                                self.columns)]

    def add(self, c):
        self.windows.append(c)

    def remove(self, c):
        self.windows.remove(c)

    def focus(self, c):
        idx = self.windows.index(c)
        self.current_window = (idx % self.columns, idx / self.columns)

    def focus_first(self):
        if self.windows:
            return self.windows[0]
        else:
            return None

    def configure(self, c, screen):
        idx = self.windows.index(c)
        column = idx % self.columns
        row = idx / self.columns
        column_size = int(math.ceil(float(len(self.windows)) / self.columns))
        if (column, row) == self.current_window:
            px = self.group.qtile.colorPixel(self.border_focus)
        else:
            px = self.group.qtile.colorPixel(self.border_normal)
        column_width = int(screen.width / float(self.columns))
        row_height = int(screen.height / float(column_size))
        xoffset = screen.x + column * column_width
        yoffset = screen.y + row * row_height
        win_width = column_width - 2 * self.border_width
        win_height = row_height - 2 * self.border_width

        c.place(xoffset,
                yoffset,
                win_width,
                win_height,
                self.border_width,
                px)
        c.unhide()

    def cmd_next(self):
        """
            Switch to the next window on current row
        """
        column, row = self.current_window
        self.current_window = (column + 1) % len(self.get_row(row)), row
        self.group.focus(self.get_current_window(), False)

    def cmd_down(self):
        """
            Switch to the next window in current column
        """
        column, row = self.current_window
        self.current_window = column, (row + 1) % len(self.get_column(column))
        self.group.focus(self.get_current_window(), False)

    def cmd_up(self):
        """
            Switch to the previous window in current column
        """
        column, row = self.current_window
        self.current_window = column, (row - 1) % len(self.get_column(column))
        self.group.focus(self.get_current_window(), False)

    def cmd_delete(self):
        """
            Decrease number of columns
        """
        self.columns -= 1
        self.group.layoutAll()

    def cmd_add(self):
        """
            Increase number of columns
        """
        self.columns += 1
        self.group.layoutAll()
