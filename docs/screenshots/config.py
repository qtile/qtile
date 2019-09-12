# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2010, 2014 dequis
# Copyright (c) 2012 Randall Ma
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 horsik
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2019 Timothée Mazzucotelli
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

from libqtile.config import Key
from libqtile.lazy import lazy
from libqtile import layout

mod = "mod4"

keys = [
    Key([mod, "control"], "q", lazy.shutdown()),
    Key([mod], "Return", lazy.spawn("xterm")),
    Key([mod], "Left", lazy.layout.left()),
    Key([mod], "Right", lazy.layout.right()),
    Key([mod], "Up", lazy.layout.up()),
    Key([mod], "Down", lazy.layout.down()),
    Key([mod], "Tab", lazy.next_layout()),
    Key([mod, "shift"], "Tab", lazy.previous_layout()),
]

border_focus = "#ff0000"
border_normal = "#000000"
border_width = 10
border = dict(
    border_focus=border_focus,
    border_normal=border_normal,
    border_width=border_width
)

layouts = [
    layout.Max(name="max"),
    layout.Bsp(name="bsp", margin=20, **border),
    layout.Columns(name="columns", **border),
    layout.Matrix(name="matrix", **border),
    layout.MonadTall(name="monadtall", **border),
    layout.MonadWide(name="monadwide", **border),
    layout.RatioTile(name="ratiotile", **border),
    # layout.Slice(name="slice"),  # Makes the session freeze
    layout.Stack(name="stack", **border),
    layout.Tile(name="tile", **border),
    layout.TreeTab(name="treetab", border_width=border_width),
    layout.VerticalTile(name="verticaltile", **border),
    layout.Zoomy(name="zoomy"),
]
