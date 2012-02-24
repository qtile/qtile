import math

from base import Layout
from .. import utils, manager


ROWCOL = 1  # do rows at a time left to right top down
COLROW = 2  # do cols top to bottom, left to right

GOLDEN_RATIO = 1.618


class GridInfo(object):
    """
    Calculates sizes for grids
    >>> gi = GridInfo(.5, 5, 600, 480)
    >>> gi.calc()
    (1, 5, 1)
    >>> gi.get_sizes()
    [(0, 0, 120, 480), (120, 0, 120, 480), (240, 0, 120, 480), (360, 0, 120, 480), (480, 0, 120, 480)]
    >>> gi = GridInfo(6, 5, 600, 480)
    >>> gi.get_sizes()
    [(0, 0, 600, 96), (0, 96, 600, 96), (0, 192, 600, 96), (0, 288, 600, 96), (0, 384, 600, 96)]
    >>> gi = GridInfo(1, 5, 600, 480)
    >>> gi.get_sizes()
    [(0, 0, 200, 240), (200, 0, 200, 240), (400, 0, 200, 240), (0, 240, 300, 240), (200, 240, 200, 240)]

    >>> foo = GridInfo(1.6, 7, 400,370)
    >>> foo.get_sizes(500,580)


    """
    def __init__(self, ratio, num_windows, width, height):
        self.ratio = ratio
        self.num_windows = num_windows
        self.width = width
        self.height = height
        self.num_rows = 0
        self.num_cols = 0

    def calc(self, num_windows, width, height):
        """
        returns (rows, cols, orientation) tuple given input
        """
        best_ratio = None
        best_rows_cols_orientation = None
        for rows, cols, orientation in self._possible_grids(num_windows):

            sample_width = float(width) / cols
            sample_height = float(height) / rows
            sample_ratio = sample_width / sample_height
            diff = abs(sample_ratio - self.ratio)
            if best_ratio is None or diff < best_ratio:
                best_ratio = diff
                best_rows_cols_orientation = rows, cols, orientation

        return best_rows_cols_orientation

    def _possible_grids(self, num_windows):
        """
        iterates over possible grids given a number of windows
        """
        if num_windows < 2:
            end = 2
        else:
            end = num_windows / 2 + 1
        for rows in range(1, end):
            cols = int(math.ceil(float(num_windows) / rows))
            yield rows, cols, ROWCOL
            if rows != cols:
                # also want the reverse test
                yield cols, rows, COLROW

    def get_sizes_advanced(self, total_width, total_height,
                           xoffset=0, yoffset=0):
        """
        after every row/column recalculate remaining area
        """
        results = []
        width = total_width
        height = total_height
        while len(results) < self.num_windows:
            remaining = self.num_windows - len(results)
            orien, sizes = self._get_row_or_col(
                remaining, width, height, xoffset, yoffset)
            results.extend(sizes)
            if orien == ROWCOL:
                # adjust height/yoffset
                height -= sizes[-1][-1]
                yoffset += sizes[-1][-1]
            else:
                width -= sizes[-1][-2]
                xoffset += sizes[-1][-2]

        return results

    def _get_row_or_col(self, num_windows, width, height, xoffset, yoffset):
        """
        process one row (or col) at a time
        """
        rows, cols, orientation = self.calc(num_windows, width, height)
        results = []
        if orientation == ROWCOL:
            x = 0
            y = 0
            for i, col in enumerate(range(cols)):
                w_width = width / cols
                w_height = height / rows
                if i == cols - 1:
                    w_width = width - x
                results.append((x + xoffset, y + yoffset, w_width, w_height))
                x += w_width
        elif orientation == COLROW:
            x = 0
            y = 0
            for i, col in enumerate(range(rows)):
                w_width = width / cols
                w_height = height / rows
                if i == rows - 1:
                    w_height = height - y
                results.append((x + xoffset, y + yoffset, w_width, w_height))
                y += w_height
        return orientation, results

    def get_sizes(self, total_width, total_height, xoffset=0, yoffset=0):
        width = 0
        height = 0
        results = []
        rows, cols, orientation = self.calc(
            self.num_windows, total_width, total_height)
        if orientation == ROWCOL:
            y = 0
            for i, row in enumerate(range(rows)):
                x = 0
                width = total_width / cols
                for j, col in enumerate(range(cols)):
                    height = total_height / rows
                    if i == rows - 1 and j == 0:
                        # last row
                        remaining = self.num_windows - len(results)
                        width = total_width / remaining
                    elif j == cols - 1 or len(results) + 1 == self.num_windows:
                        # since we are dealing with integers,
                        # make last column (or item) take up remaining space
                        width = total_width - x

                    results.append((x + xoffset, y + yoffset,
                                    width,
                                    height))
                    if len(results) == self.num_windows:
                        return results
                    x += width
                y += height
        else:
            x = 0
            for i, col in enumerate(range(cols)):
                y = 0
                height = total_height / rows
                for j, row in enumerate(range(rows)):
                    width = total_width / cols
                    # down first
                    if i == cols - 1 and j == 0:
                        remaining = self.num_windows - len(results)
                        height = total_height / remaining
                    elif j == rows - 1 or len(results) + 1 == self.num_windows:
                        height = total_height - y
                    results.append((x + xoffset,  # i * width + xoffset,
                                    y + xoffset,  # j * height + yoffset,
                                    width,
                                    height))
                    if len(results) == self.num_windows:
                        return results
                    y += height
                x += width

        return results


class RatioTile(Layout):
    """
    Tries to tile all windows in the width/height ratio passed in
    """
    defaults = manager.Defaults(
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width."),
        ("name", "ratiotile", "Name of this layout."),
    )

    def __init__(self, ratio=GOLDEN_RATIO, ratio_increment=0.1,
                 fancy=False, **config):
        Layout.__init__(self, **config)
        self.windows = []
        self.ratio_increment = ratio_increment
        self.ratio = ratio
        self.focused = None
        self.dirty = True  # need to recalculate
        self.layout_info = []
        self.last_size = None
        self.last_screen = None
        self.fancy = fancy

    def clone(self, group):
        c = Layout.clone(self, group)
        c.windows = []
        return c

    def focus(self, c):
        self.focused = c

    def blur(self):
        self.focused = None

    def add(self, w):
        self.dirty = True
        self.windows.insert(0, w)

    def remove(self, w):
        self.dirty = True
        if self.focused is w:
            self.focused = None
        self.windows.remove(w)
        if self.windows:  # and w is self.focused:
            self.focused = self.windows[0]
        return self.focused

    def configure(self, win, screen):
        # force recalc
        if not self.last_screen or self.last_screen != screen:
            self.last_screen = screen
            self.dirty = True
        if self.last_size and not self.dirty:
            if (screen.width != self.last_size[0] or
                screen.height != self.last_size[1]):
                self.dirty = True
        if self.dirty:
            gi = GridInfo(self.ratio, len(self.windows),
                          screen.width,
                          screen.height)
            self.last_size = screen.width, screen.height
            if self.fancy:
                method = gi.get_sizes_advanced
            else:
                method = gi.get_sizes

            self.layout_info = method(screen.width,
                                      screen.height,
                                      screen.x,
                                      screen.y)

            self.dirty = False
        try:
            idx = self.windows.index(win)
        except ValueError:
            win.hide()
            return
        x, y, w, h = self.layout_info[idx]
        if win is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        win.place(x, y, w - self.border_width * 2, h - self.border_width * 2,
                  self.border_width, bc)
        win.unhide()

    def info(self):
        return {'windows': [x.name for x in self.windows],
                'ratio': self.ratio,
                'focused': self.focused.name if self.focused else None,
                'layout_info': self.layout_info
        }

    def up(self):
        if self.windows:
            utils.shuffleUp(self.windows)
            self.group.layoutAll()

    def down(self):
        if self.windows:
            utils.shuffleDown(self.windows)
            self.group.layoutAll()

    def focus_first(self):
        if self.windows:
            return self.windows[0]

    def focus_next(self, win):
        idx = self.windows.index(win)
        if len(self.windows) > idx + 1:
            return self.windows[idx + 1]

    def focus_last(self):
        if self.windows:
            return self.windows[-1]

    def focus_prev(self, win):
        idx = self.windows.index(win)
        if idx > 0:
            return self.windows[idx - 1]

    def getNextClient(self):
        nextindex = self.windows.index(self.focused) + 1
        if nextindex >= len(self.windows):
            nextindex = 0
        return self.windows[nextindex]

    def getPreviousClient(self):
        previndex = self.windows.index(self.focused) - 1
        if previndex < 0:
            previndex = len(self.windows) - 1
        return self.windows[previndex]

    def next(self):
        n = self.getPreviousClient()
        self.group.focus(n, True)

    def previous(self):
        n = self.getNextClient()
        self.group.focus(n, True)

    def shuffle(self, function):
        if self.windows:
            function(self.windows)
            self.group.layoutAll()

    def cmd_down(self):
        self.down()

    def cmd_up(self):
        self.up()

    def cmd_next(self):
        self.next()

    def cmd_previous(self):
        self.previous()

    def cmd_decrease_ratio(self):
        new_ratio = self.ratio - self.ratio_increment
        if new_ratio < 0:
            return
        self.ratio = new_ratio
        self.group.layoutAll()

    def cmd_increase_ratio(self):
        self.ratio += self.ratio_increment
        self.group.layoutAll()

    def cmd_info(self):
        return self.info()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
