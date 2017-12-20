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

import pytest

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..conftest import no_xinerama
from .layout_utils import assertFocused, assertFocusPath


class ColumnsConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Columns(),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def columns_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [ColumnsConfig], indirect=True)(x))

# This currently only tests the window focus cycle


@columns_config
def test_columns_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("float1")
    qtile.c.window.toggle_floating()
    qtile.testWindow("float2")
    qtile.c.window.toggle_floating()
    qtile.testWindow("three")

    # test preconditions, columns adds clients at pos after current, in two stacks
    assert qtile.c.layout.info()['columns'][0]['clients'] == ['one']
    assert qtile.c.layout.info()['columns'][1]['clients'] == ['two', 'three']
    # last added window has focus
    assertFocused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assertFocusPath(qtile, 'two', 'float1', 'float2', 'one', 'three')
