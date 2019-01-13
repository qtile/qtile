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

from .bsp import Bsp
from .columns import Columns
from .floating import Floating
from .matrix import Matrix
from .max import Max
from .ratiotile import RatioTile
from .slice import Slice
from .stack import Stack
from .tile import Tile
from .tree import TreeTab
from .verticaltile import VerticalTile
from .xmonad import MonadTall, MonadWide
from .zoomy import Zoomy
