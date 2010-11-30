import math

from base import Layout
from .. import utils, manager


ROWCOL = 1 # do rows at a time left to right top down
COLROW = 2 # do cols top to bottom, left to right

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


    """
    def __init__(self, ratio, num_windows, width, height):
        self.ratio = ratio
        self.num_windows = num_windows
        self.width = width
        self.height = height
        self.num_rows = 0
        self.num_cols = 0

    def calc(self):
        #print "TRYING TO MATCH", self.ratio
        best_ratio = None
        best_rows_cols_orientation = None
        for rows, cols, orientation in self._possible_grids():

            sample_width = float(self.width)/cols
            sample_height = float(self.height)/rows
            sample_ratio = sample_width / sample_height
            diff = abs(sample_ratio - self.ratio)
            #print "ROWS %s cols %s ratio %s diff %s best %s" %(rows, cols, sample_ratio, diff, best_ratio)
            if best_ratio is None or diff < best_ratio:
                #print "\tbest"
                best_ratio = diff
                best_rows_cols_orientation = rows, cols, orientation

        return best_rows_cols_orientation

    def _possible_grids(self):
        if self.num_windows < 2:
            end = 2
        else:
            end = self.num_windows/2 + 1
        for rows in range(1, end):
            cols = int(math.ceil(float(self.num_windows) / rows))
            yield rows, cols, ROWCOL
            if rows != cols:
                # also want the reverse test
                yield cols, rows, COLROW

    def get_sizes(self, xoffset=0, yoffset=0):


        width = 0
        height = 0
        results = []
        rows, cols, orientation = self.calc()
        if orientation == ROWCOL:
            y = yoffset
            for i, row in enumerate(range(rows)):
                x = xoffset
                width = self.width/cols
                for j, col in enumerate(range(cols)):
                    height = self.height/rows
                    if i == rows - 1 and j == 0:
                        # last row
                        remaining = self.num_windows - len(results) 
                        width = self.width/remaining
                    elif j == cols - 1 or len(results) + 1 == self.num_windows:
                        # since we are dealing with integers,
                        # make last column (or item) take up remaining space
                        width = self.width - x
                    
                    results.append((x, y,
                                    width,
                                    height))
                    if len(results) == self.num_windows:
                        return results
                    x += width
                y += height
        else:
            x = xoffset
            for i, col in enumerate(range(cols)):
                y = yoffset
                height = self.height/rows
                for j, row in enumerate(range(rows)):
                    width = self.width/cols
                    # down first
                    if i == cols - 1 and j == 0:
                        remaining = self.num_windows - len(results) 
                        height = self.height/remaining
                    elif j == rows -1 or len(results) + 1 == self.num_windows:
                        height = self.height - y
                    results.append((x, #i * width + xoffset,
                                    y, #j * height + yoffset,
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
    name="ratiotile"
    defaults = manager.Defaults(
        ("border_focus", "#0000ff", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused winows."),
        ("border_width", 1, "Border width.")
    )
    
    def __init__(self, ratio=GOLDEN_RATIO, ratio_increment=0.1, **config):
        Layout.__init__(self, **config)
        self.windows = []
        self.ratio_increment = ratio_increment
        self.ratio = ratio
        self.focused = None
        self.dirty = True # need to recalculate
        self.layout_info = None

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
        if self.windows and w is self.focused:
            self.focused = self.windows[0]
        return self.focused

    def configure(self, win):
        try:
            idx = self.windows.index(win)
        except ValueError:
            win.hide()
            return
        
        if self.dirty:
            gi = GridInfo(self.ratio, len(self.windows),
                          self.group.screen.dwidth,
                          self.group.screen.dheight)
            self.layout_info = gi.get_sizes(self.group.screen.dx,
                                            self.group.screen.dy)

            self.dirty = False
        x, y, w, h = self.layout_info[idx]
        if win is self.focused:
            bc = self.group.qtile.colorPixel(self.border_focus)
        else:
            bc = self.group.qtile.colorPixel(self.border_normal)
        win.place(x, y, w-self.border_width*2, h-self.border_width*2,
                  self.border_width, bc)
        win.unhide()

    def info(self):
        return { 'windows': [x.name for x in self.windows],
                 'ratio' :self.ratio,
                 'focused' : self.focused.name if self.focused else None,
                 'layout_info' : self.layout_info
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
        if len(self.windows) > idx+1:
            return self.windows[idx+1]

    def focus_last(self):
        if self.windows:
            return self.windows[-1]

    def focus_prev(self, win):
        idx = self.windows.index(win)
        if idx > 0:
            return self.windows[idx-1]

    def getNextClient(self):
        nextindex = self.windows.index(self.focused) + 1
        if nextindex >= len(self.windows):
            nextindex = 0
        return self.windows[nextindex]

    def getPreviousClient(self):
        previndex = self.windows.index(self.focused) - 1
        if previndex < 0:
            previndex = len(self.windows) - 1;
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
        new_ratio = self.ratio -  self.ratio_increment
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
