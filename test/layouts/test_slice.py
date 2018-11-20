# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Chris Wesseling
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
from .layout_utils import assert_dimensions, assertFocused, assertFocusPath
from ..conftest import no_xinerama


class SliceConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [
        layout.Slice(side='left', width=200, wname='slice',
                     fallback=layout.Stack(num_stacks=1, border_width=0)),
        layout.Slice(side='right', width=200, wname='slice',
                     fallback=layout.Stack(num_stacks=1, border_width=0)),
        layout.Slice(side='top', width=200, wname='slice',
                     fallback=layout.Stack(num_stacks=1, border_width=0)),
        layout.Slice(side='bottom', width=200, wname='slice',
                     fallback=layout.Stack(num_stacks=1, border_width=0)),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def slice_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [SliceConfig], indirect=True)(x))


@slice_config
def test_no_slice(qtile):
    qtile.testWindow('one')
    assert_dimensions(qtile, 200, 0, 600, 600)
    qtile.testWindow('two')
    assert_dimensions(qtile, 200, 0, 600, 600)


@slice_config
def test_slice_first(qtile):
    qtile.testWindow('slice')
    assert_dimensions(qtile, 0, 0, 200, 600)
    qtile.testWindow('two')
    assert_dimensions(qtile, 200, 0, 600, 600)


@slice_config
def test_slice_last(qtile):
    qtile.testWindow('one')
    assert_dimensions(qtile, 200, 0, 600, 600)
    qtile.testWindow('slice')
    assert_dimensions(qtile, 0, 0, 200, 600)


@slice_config
def test_slice_focus(qtile):
    qtile.testWindow('one')
    assertFocused(qtile, 'one')
    two = qtile.testWindow('two')
    assertFocused(qtile, 'two')
    slice = qtile.testWindow('slice')
    assertFocused(qtile, 'slice')
    assertFocusPath(qtile, 'slice')
    qtile.testWindow('three')
    assertFocusPath(qtile, 'two', 'one', 'slice', 'three')
    qtile.kill_window(two)
    assertFocusPath(qtile, 'one', 'slice', 'three')
    qtile.kill_window(slice)
    assertFocusPath(qtile, 'one', 'three')
    slice = qtile.testWindow('slice')
    assertFocusPath(qtile, 'three', 'one', 'slice')


@slice_config
def test_all_slices(qtile):
    qtile.testWindow('slice')  # left
    assert_dimensions(qtile, 0, 0, 200, 600)
    qtile.c.next_layout()  # right
    assert_dimensions(qtile, 600, 0, 200, 600)
    qtile.c.next_layout()  # top
    assert_dimensions(qtile, 0, 0, 800, 200)
    qtile.c.next_layout()  # bottom
    assert_dimensions(qtile, 0, 400, 800, 200)
    qtile.c.next_layout()  # left again
    qtile.testWindow('one')
    assert_dimensions(qtile, 200, 0, 600, 600)
    qtile.c.next_layout()  # right
    assert_dimensions(qtile, 0, 0, 600, 600)
    qtile.c.next_layout()  # top
    assert_dimensions(qtile, 0, 200, 800, 400)
    qtile.c.next_layout()  # bottom
    assert_dimensions(qtile, 0, 0, 800, 400)


@slice_config
def test_command_propagation(qtile):
    qtile.testWindow('slice')
    qtile.testWindow('one')
    qtile.testWindow('two')
    info = qtile.c.layout.info()
    assert info['name'] == 'slice', info['name']
    org_height = qtile.c.window.info()['height']
    qtile.c.layout.toggle_split()
    assert qtile.c.window.info()['height'] != org_height
