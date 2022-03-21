# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Florian Scherf
# Copyright (c) 2014 Tycho Andersen
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

# https://bitbucket.org/tarek/flake8/issue/141/improve-flake8-statement-to-ignore
# is annoying, so we ignore libqtile/layout/__init__.py completely
# flake8: noqa

from libqtile.layout.bsp import Bsp
from libqtile.layout.columns import Columns
from libqtile.layout.floating import Floating
from libqtile.layout.matrix import Matrix
from libqtile.layout.max import Max
from libqtile.layout.ratiotile import RatioTile
from libqtile.layout.slice import Slice
from libqtile.layout.spiral import Spiral
from libqtile.layout.stack import Stack
from libqtile.layout.tile import Tile
from libqtile.layout.tree import TreeTab
from libqtile.layout.verticaltile import VerticalTile
from libqtile.layout.xmonad import MonadTall, MonadWide, MonadThreeCol
from libqtile.layout.zoomy import Zoomy
