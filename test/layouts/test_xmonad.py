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

import pytest

from libqtile import layout
import libqtile.manager
import libqtile.config
from .layout_utils import assertDimensions, assertFocused
from ..conftest import no_xinerama


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


monadtall_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [MonadTallConfig], indirect=True)(x))


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


monadtallmargins_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [MonadTallMarginsConfig], indirect=True)(x))


@monadtall_config
def test_add_clients(qtile):
    qtile.testWindow('one')
    qtile.testWindow('two')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two']
    assertFocused(qtile, 'two')

    qtile.testWindow('three')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'three']
    assertFocused(qtile, 'three')

    qtile.c.layout.previous()
    assertFocused(qtile, 'two')

    qtile.testWindow('four')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assertFocused(qtile, 'four')


@monadtallmargins_config
def test_margins(qtile):
    qtile.testWindow('one')
    assertDimensions(qtile, 4, 4, 788, 588)

    qtile.testWindow('two')
    assertFocused(qtile, 'two')
    assertDimensions(qtile, 404, 4, 388, 588)

    qtile.c.layout.previous()
    assertFocused(qtile, 'one')
    assertDimensions(qtile, 4, 4, 392, 588)


@monadtall_config
def test_growmain_solosecondary(qtile):
    qtile.testWindow('one')
    assertDimensions(qtile, 0, 0, 796, 596)

    qtile.testWindow('two')
    qtile.c.layout.previous()
    assertFocused(qtile, 'one')

    assertDimensions(qtile, 0, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(qtile, 0, 0, 436, 596)
    qtile.c.layout.shrink()
    assertDimensions(qtile, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assertDimensions(qtile, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assertDimensions(qtile, 0, 0, 196, 596)


@monadtall_config
def test_growmain_multiplesecondary(qtile):
    qtile.testWindow('one')
    assertDimensions(qtile, 0, 0, 796, 596)

    qtile.testWindow('two')
    qtile.testWindow('three')
    qtile.c.layout.previous()
    qtile.c.layout.previous()
    assertFocused(qtile, 'one')

    assertDimensions(qtile, 0, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(qtile, 0, 0, 436, 596)
    qtile.c.layout.shrink()
    assertDimensions(qtile, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assertDimensions(qtile, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assertDimensions(qtile, 0, 0, 196, 596)


@monadtall_config
def test_growsecondary_solosecondary(qtile):
    qtile.testWindow('one')
    assertDimensions(qtile, 0, 0, 796, 596)

    qtile.testWindow('two')
    assertFocused(qtile, 'two')

    assertDimensions(qtile, 400, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assertDimensions(qtile, 360, 0, 436, 596)
    qtile.c.layout.shrink()
    assertDimensions(qtile, 400, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assertDimensions(qtile, 200, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assertDimensions(qtile, 600, 0, 196, 596)


@monadtall_config
def test_growsecondary_multiplesecondary(qtile):
    qtile.testWindow('one')
    assertDimensions(qtile, 0, 0, 796, 596)

    qtile.testWindow('two')
    qtile.testWindow('three')
    qtile.c.layout.previous()
    assertFocused(qtile, 'two')

    assertDimensions(qtile, 400, 0, 396, 296)
    # Grow 20 pixels
    qtile.c.layout.grow()
    assertDimensions(qtile, 400, 0, 396, 316)
    qtile.c.layout.shrink()
    assertDimensions(qtile, 400, 0, 396, 296)

    # Min height of other is 85 pixels, leaving 515
    for _ in range(20):
        qtile.c.layout.grow()
    assertDimensions(qtile, 400, 0, 396, 511)

    # Min height of qtile is 85 pixels
    for _ in range(40):
        qtile.c.layout.shrink()
    assertDimensions(qtile, 400, 0, 396, 85)


@monadtall_config
def test_flip(qtile):
    qtile.testWindow('one')
    qtile.testWindow('two')
    qtile.testWindow('three')

    # Check all the dimensions
    qtile.c.layout.next()
    assertFocused(qtile, 'one')
    assertDimensions(qtile, 0, 0, 396, 596)

    qtile.c.layout.next()
    assertFocused(qtile, 'two')
    assertDimensions(qtile, 400, 0, 396, 296)

    qtile.c.layout.next()
    assertFocused(qtile, 'three')
    assertDimensions(qtile, 400, 300, 396, 296)

    # Now flip it and do it again
    qtile.c.layout.flip()

    qtile.c.layout.next()
    assertFocused(qtile, 'one')
    assertDimensions(qtile, 400, 0, 396, 596)

    qtile.c.layout.next()
    assertFocused(qtile, 'two')
    assertDimensions(qtile, 0, 0, 396, 296)

    qtile.c.layout.next()
    assertFocused(qtile, 'three')
    assertDimensions(qtile, 0, 300, 396, 296)


@monadtall_config
def test_shuffle(qtile):
    qtile.testWindow('one')
    qtile.testWindow('two')
    qtile.testWindow('three')
    qtile.testWindow('four')

    assert qtile.c.layout.info()['main'] == 'one'
    assert qtile.c.layout.info()['secondary'] == ['two', 'three', 'four']

    qtile.c.layout.shuffle_up()
    assert qtile.c.layout.info()['main'] == 'one'
    assert qtile.c.layout.info()['secondary'] == ['two', 'four', 'three']

    qtile.c.layout.shuffle_up()
    assert qtile.c.layout.info()['main'] == 'one'
    assert qtile.c.layout.info()['secondary'] == ['four', 'two', 'three']

    qtile.c.layout.shuffle_up()
    assert qtile.c.layout.info()['main'] == 'four'
    assert qtile.c.layout.info()['secondary'] == ['one', 'two', 'three']


@monadtall_config
def test_swap(qtile):
    qtile.testWindow('one')
    qtile.testWindow('two')
    qtile.testWindow('three')
    qtile.testWindow('focused')

    assert qtile.c.layout.info()['main'] == 'one'
    assert qtile.c.layout.info()['secondary'] == ['two', 'three', 'focused']

    # Swap a secondary left, left aligned
    qtile.c.layout.swap_left()
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['two', 'three', 'one']

    # Swap a main right, left aligned
    qtile.c.layout.swap_right()
    assert qtile.c.layout.info()['main'] == 'two'
    assert qtile.c.layout.info()['secondary'] == ['focused', 'three', 'one']

    # flip over
    qtile.c.layout.flip()
    qtile.c.layout.shuffle_down()
    assert qtile.c.layout.info()['main'] == 'two'
    assert qtile.c.layout.info()['secondary'] == ['three', 'focused', 'one']

    # Swap secondary right, right aligned
    qtile.c.layout.swap_right()
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['three', 'two', 'one']

    # Swap main left, right aligned
    qtile.c.layout.swap_left()
    assert qtile.c.layout.info()['main'] == 'three'
    assert qtile.c.layout.info()['secondary'] == ['focused', 'two', 'one']

    # Do swap main
    qtile.c.layout.swap_main()
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['three', 'two', 'one']
