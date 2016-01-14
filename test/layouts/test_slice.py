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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..utils import Xephyr
from .layout_utils import assertDimensions, assertFocused, assertFocusPath


class SliceConfig:
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


@Xephyr(False, SliceConfig())
def test_no_slice(self):
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.testWindow('two')
    assertDimensions(self, 200, 0, 600, 600)


@Xephyr(False, SliceConfig())
def test_slice_first(self):
    self.testWindow('slice')
    assertDimensions(self, 0, 0, 200, 600)
    self.testWindow('two')
    assertDimensions(self, 200, 0, 600, 600)


@Xephyr(False, SliceConfig())
def test_slice_last(self):
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.testWindow('slice')
    assertDimensions(self, 0, 0, 200, 600)


@Xephyr(False, SliceConfig())
def test_slice_focus(self):
    one = self.testWindow('one')
    assertFocused(self, 'one')
    two = self.testWindow('two')
    assertFocused(self, 'two')
    slice = self.testWindow('slice')
    assertFocused(self, 'slice')
    assertFocusPath(self, 'slice')
    three = self.testWindow('three')
    assertFocusPath(self, 'slice', 'three')
    self.kill(two)
    assertFocusPath(self, 'slice', 'one')
    self.kill(slice)
    assertFocusPath(self, 'one')
    slice = self.testWindow('slice')
    assertFocusPath(self, 'one', 'slice')


@Xephyr(False, SliceConfig())
def test_all_slices(self):
    self.testWindow('slice')  # left
    assertDimensions(self, 0, 0, 200, 600)
    self.c.next_layout()  # right
    assertDimensions(self, 600, 0, 200, 600)
    self.c.next_layout()  # top
    assertDimensions(self, 0, 0, 800, 200)
    self.c.next_layout()  # bottom
    assertDimensions(self, 0, 400, 800, 200)
    self.c.next_layout()  # left again
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.c.next_layout()  # right
    assertDimensions(self, 0, 0, 600, 600)
    self.c.next_layout()  # top
    assertDimensions(self, 0, 200, 800, 400)
    self.c.next_layout()  # bottom
    assertDimensions(self, 0, 0, 800, 400)


@Xephyr(False, SliceConfig())
def test_command_propagation(self):
    self.testWindow('slice')
    self.testWindow('one')
    self.testWindow('two')
    info = self.c.layout.info()
    assert info['name'] == 'slice', info['name']
    org_height = self.c.window.info()['height']
    self.c.layout.toggle_split()
    assert self.c.window.info()['height'] != org_height
