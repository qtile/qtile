# Copyright (C) 2016, zordsdavini
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

import re

from .dmenu import Dmenu

class WindowList():
    """
    Give vertical list of all open windows in dmenu. Switch to selected.
    """
    config = {}
    qtile = None
    wins = []
    id_map = {}

    def __init__(self, qtile):
        self.qtile = qtile
        if hasattr(qtile.config, 'extentions') and qtile.config.extentions['dmenu']:
            self.config = qtile.config.extentions['dmenu']

    def get_windows(self):
        id = 0
        self.wins = []
        self.id_map = {}
        for win in self.qtile.windowMap.values():
            if win.group:
                self.wins.append("%i: %s (%s)" % (id, win.name, win.group.name))
                self.id_map[id] = win
                id = id + 1

        return id

    def run(self):
        win_count = self.get_windows()
        config_tmp = self.config
        dmenu = Dmenu(config_tmp, win_count)
        out = dmenu.call(self.wins)
        if not out:
            return

        id = int(re.match(b"^\d+", out).group())
        win = self.id_map[id]
        screen = self.qtile.currentScreen
        screen.setGroup(win.group)
        win.group.focus(win)
