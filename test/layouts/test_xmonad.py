# Copyright (c) 2015 Sean Vig
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
from .layout_utils import assertDimensions, assertFocused


class MonadTallConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadTall()
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


class MonadTallMarginsConfig(object):
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadTall(margin=4)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@Xephyr(False, MonadTallConfig())
def test_add_clients(self):
    self.testWindow('one')
    self.testWindow('two')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two']
    assertFocused(self, 'two')

    self.testWindow('three')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'three']
    assertFocused(self, 'three')

    self.c.layout.previous()
    assertFocused(self, 'two')

    self.testWindow('four')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assertFocused(self, 'four')


@Xephyr(False, MonadTallMarginsConfig())
def test_margins(self):
    self.testWindow('one')
    assertDimensions(self, 4, 4, 788, 588)

    self.testWindow('two')
    assertFocused(self, 'two')
    assertDimensions(self, 404, 4, 388, 588)

    self.c.layout.previous()
    assertFocused(self, 'one')
    assertDimensions(self, 4, 4, 392, 588)


@Xephyr(False, MonadTallConfig())
def test_growmain_solosecondary(self):
    self.testWindow('one')
    assertDimensions(self, 0, 0, 796, 596)

    self.testWindow('two')
    self.c.layout.previous()
    assertFocused(self, 'one')

    assertDimensions(self, 0, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(self, 0, 0, 436, 596)
    self.c.layout.shrink()
    assertDimensions(self, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assertDimensions(self, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assertDimensions(self, 0, 0, 196, 596)


@Xephyr(False, MonadTallConfig())
def test_growmain_multiplesecondary(self):
    self.testWindow('one')
    assertDimensions(self, 0, 0, 796, 596)

    self.testWindow('two')
    self.testWindow('three')
    self.c.layout.previous()
    self.c.layout.previous()
    assertFocused(self, 'one')

    assertDimensions(self, 0, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(self, 0, 0, 436, 596)
    self.c.layout.shrink()
    assertDimensions(self, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assertDimensions(self, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assertDimensions(self, 0, 0, 196, 596)


@Xephyr(False, MonadTallConfig())
def test_growsecondary_solosecondary(self):
    self.testWindow('one')
    assertDimensions(self, 0, 0, 796, 596)

    self.testWindow('two')
    assertFocused(self, 'two')

    assertDimensions(self, 400, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(self, 360, 0, 436, 596)
    self.c.layout.shrink()
    assertDimensions(self, 400, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assertDimensions(self, 200, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assertDimensions(self, 600, 0, 196, 596)


@Xephyr(False, MonadTallConfig())
def test_growsecondary_multiplesecondary(self):
    self.testWindow('one')
    assertDimensions(self, 0, 0, 796, 596)

    self.testWindow('two')
    self.testWindow('three')
    self.c.layout.previous()
    assertFocused(self, 'two')

    assertDimensions(self, 400, 0, 396, 296)
    # Grow 20 pixels
    self.c.layout.grow()
    assertDimensions(self, 400, 0, 396, 316)
    self.c.layout.shrink()
    assertDimensions(self, 400, 0, 396, 296)

    # Min height of other is 85 pixels, leaving 515
    for _ in range(20):
        self.c.layout.grow()
    assertDimensions(self, 400, 0, 396, 511)

    # Min height of self is 85 pixels
    for _ in range(40):
        self.c.layout.shrink()
    assertDimensions(self, 400, 0, 396, 85)


@Xephyr(False, MonadTallConfig())
def test_flip(self):
    self.testWindow('one')
    self.testWindow('two')
    self.testWindow('three')

    # Check all the dimensions
    self.c.layout.next()
    assertFocused(self, 'one')
    assertDimensions(self, 0, 0, 396, 596)

    self.c.layout.next()
    assertFocused(self, 'two')
    assertDimensions(self, 400, 0, 396, 296)

    self.c.layout.next()
    assertFocused(self, 'three')
    assertDimensions(self, 400, 300, 396, 296)

    # Now flip it and do it again
    self.c.layout.flip()

    self.c.layout.next()
    assertFocused(self, 'one')
    assertDimensions(self, 400, 0, 396, 596)

    self.c.layout.next()
    assertFocused(self, 'two')
    assertDimensions(self, 0, 0, 396, 296)

    self.c.layout.next()
    assertFocused(self, 'three')
    assertDimensions(self, 0, 300, 396, 296)


@Xephyr(False, MonadTallConfig())
def test_shuffle(self):
    self.testWindow('one')
    self.testWindow('two')
    self.testWindow('three')
    self.testWindow('four')

    assert self.c.layout.info()['main'] == 'one'
    assert self.c.layout.info()['secondary'] == ['two', 'three', 'four']

    self.c.layout.shuffle_up()
    assert self.c.layout.info()['main'] == 'one'
    assert self.c.layout.info()['secondary'] == ['two', 'four', 'three']

    self.c.layout.shuffle_up()
    assert self.c.layout.info()['main'] == 'one'
    assert self.c.layout.info()['secondary'] == ['four', 'two', 'three']

    self.c.layout.shuffle_up()
    assert self.c.layout.info()['main'] == 'four'
    assert self.c.layout.info()['secondary'] == ['one', 'two', 'three']


@Xephyr(False, MonadTallConfig())
def test_swap(self):
    self.testWindow('one')
    self.testWindow('two')
    self.testWindow('three')
    self.testWindow('focused')

    assert self.c.layout.info()['main'] == 'one'
    assert self.c.layout.info()['secondary'] == ['two', 'three', 'focused']

    # Swap a secondary left, left aligned
    self.c.layout.swap_left()
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['two', 'three', 'one']

    # Swap a main right, left aligned
    self.c.layout.swap_right()
    assert self.c.layout.info()['main'] == 'two'
    assert self.c.layout.info()['secondary'] == ['focused', 'three', 'one']

    # flip over
    self.c.layout.flip()
    self.c.layout.shuffle_down()
    assert self.c.layout.info()['main'] == 'two'
    assert self.c.layout.info()['secondary'] == ['three', 'focused', 'one']

    # Swap secondary right, right aligned
    self.c.layout.swap_right()
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['three', 'two', 'one']

    # Swap main left, right aligned
    self.c.layout.swap_left()
    assert self.c.layout.info()['main'] == 'three'
    assert self.c.layout.info()['secondary'] == ['focused', 'two', 'one']

    # Do swap main
    self.c.layout.swap_main()
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['three', 'two', 'one']
