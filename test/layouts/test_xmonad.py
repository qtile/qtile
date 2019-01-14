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
from .layout_utils import assert_dimensions, assert_focused, assert_focus_path
from ..conftest import no_xinerama


class MonadTallConfig:
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


def monadtall_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MonadTallConfig], indirect=True)(x))


class MonadTallMarginsConfig:
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


def monadtallmargins_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MonadTallMarginsConfig], indirect=True)(x))


class MonadWideConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadWide()
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadwide_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MonadWideConfig], indirect=True)(x))


class MonadWideMarginsConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadWide(margin=4)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadwidemargins_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [MonadWideMarginsConfig], indirect=True)(x))


@monadtall_config
def test_tall_add_clients(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two']
    assert_focused(qtile, 'two')

    qtile.test_window('three')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'three']
    assert_focused(qtile, 'three')

    qtile.c.layout.previous()
    assert_focused(qtile, 'two')

    qtile.test_window('four')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assert_focused(qtile, 'four')


@monadwide_config
def test_wide_add_clients(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two']
    assert_focused(qtile, 'two')

    qtile.test_window('three')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'three']
    assert_focused(qtile, 'three')

    qtile.c.layout.previous()
    assert_focused(qtile, 'two')

    qtile.test_window('four')
    assert qtile.c.layout.info()["main"] == 'one'
    assert qtile.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assert_focused(qtile, 'four')


@monadtallmargins_config
def test_tall_margins(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 4, 4, 788, 588)

    qtile.test_window('two')
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 404, 4, 388, 588)

    qtile.c.layout.previous()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 4, 4, 392, 588)


@monadwidemargins_config
def test_wide_margins(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 4, 4, 788, 588)

    qtile.test_window('two')
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 4, 304, 788, 288)

    qtile.c.layout.previous()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 4, 4, 788, 292)


@monadtall_config
def test_tall_growmain_solosecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.c.layout.previous()
    assert_focused(qtile, 'one')

    assert_dimensions(qtile, 0, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(qtile, 0, 0, 436, 596)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_solosecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.c.layout.previous()
    assert_focused(qtile, 'one')

    assert_dimensions(qtile, 0, 0, 796, 296)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 30 pixels
    assert_dimensions(qtile, 0, 0, 796, 326)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 796, 146)


@monadtall_config
def test_tall_growmain_multiplesecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.test_window('three')
    qtile.c.layout.previous()
    qtile.c.layout.previous()
    assert_focused(qtile, 'one')

    assert_dimensions(qtile, 0, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(qtile, 0, 0, 436, 596)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_multiplesecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.test_window('three')
    qtile.c.layout.previous()
    qtile.c.layout.previous()
    assert_focused(qtile, 'one')

    assert_dimensions(qtile, 0, 0, 796, 296)
    qtile.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(qtile, 0, 0, 796, 326)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 0, 796, 146)


@monadtall_config
def test_tall_growsecondary_solosecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    assert_focused(qtile, 'two')

    assert_dimensions(qtile, 400, 0, 396, 596)
    qtile.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(qtile, 360, 0, 436, 596)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 400, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 200, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 600, 0, 196, 596)


@monadwide_config
def test_wide_growsecondary_solosecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    assert_focused(qtile, 'two')

    assert_dimensions(qtile, 0, 300, 796, 296)
    qtile.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(qtile, 0, 270, 796, 326)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 300, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 150, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 450, 796, 146)


@monadtall_config
def test_tall_growsecondary_multiplesecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.test_window('three')
    qtile.c.layout.previous()
    assert_focused(qtile, 'two')

    assert_dimensions(qtile, 400, 0, 396, 296)
    # Grow 20 pixels
    qtile.c.layout.grow()
    assert_dimensions(qtile, 400, 0, 396, 316)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 400, 0, 396, 296)

    # Min height of other is 85 pixels, leaving 515
    for _ in range(20):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 400, 0, 396, 511)

    # Min height of qtile is 85 pixels
    for _ in range(40):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 400, 0, 396, 85)


@monadwide_config
def test_wide_growsecondary_multiplesecondary(qtile):
    qtile.test_window('one')
    assert_dimensions(qtile, 0, 0, 796, 596)

    qtile.test_window('two')
    qtile.test_window('three')
    qtile.c.layout.previous()
    assert_focused(qtile, 'two')

    assert_dimensions(qtile, 0, 300, 396, 296)
    # Grow 20 pixels
    qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 300, 416, 296)
    qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 300, 396, 296)

    # Min width of other is 85 pixels, leaving 715
    for _ in range(20):
        qtile.c.layout.grow()
    assert_dimensions(qtile, 0, 300, 710, 296)  # TODO why not 711 ?

    # Min width of qtile is 85 pixels
    for _ in range(40):
        qtile.c.layout.shrink()
    assert_dimensions(qtile, 0, 300, 85, 296)


@monadtall_config
def test_tall_flip(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')

    # Check all the dimensions
    qtile.c.layout.next()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 0, 0, 396, 596)

    qtile.c.layout.next()
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 400, 0, 396, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'three')
    assert_dimensions(qtile, 400, 300, 396, 296)

    # Now flip it and do it again
    qtile.c.layout.flip()

    qtile.c.layout.next()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 400, 0, 396, 596)

    qtile.c.layout.next()
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 0, 0, 396, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'three')
    assert_dimensions(qtile, 0, 300, 396, 296)


@monadwide_config
def test_wide_flip(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')

    # Check all the dimensions
    qtile.c.layout.next()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 0, 0, 796, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 0, 300, 396, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'three')
    assert_dimensions(qtile, 400, 300, 396, 296)

    # Now flip it and do it again
    qtile.c.layout.flip()

    qtile.c.layout.next()
    assert_focused(qtile, 'one')
    assert_dimensions(qtile, 0, 300, 796, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'two')
    assert_dimensions(qtile, 0, 0, 396, 296)

    qtile.c.layout.next()
    assert_focused(qtile, 'three')
    assert_dimensions(qtile, 400, 0, 396, 296)


@monadtall_config
def test_tall_shuffle(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')
    qtile.test_window('four')

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


@monadwide_config
def test_wide_shuffle(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')
    qtile.test_window('four')

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
def test_tall_swap(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')
    qtile.test_window('focused')

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


@monadwide_config
def test_wide_swap(qtile):
    qtile.test_window('one')
    qtile.test_window('two')
    qtile.test_window('three')
    qtile.test_window('focused')

    assert qtile.c.layout.info()['main'] == 'one'
    assert qtile.c.layout.info()['secondary'] == ['two', 'three', 'focused']

    # Swap a secondary up
    qtile.c.layout.swap_right()  # equivalent to swap_down
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['two', 'three', 'one']

    # Swap a main down
    qtile.c.layout.swap_left()  # equivalent to swap up
    assert qtile.c.layout.info()['main'] == 'two'
    assert qtile.c.layout.info()['secondary'] == ['focused', 'three', 'one']

    # flip over
    qtile.c.layout.flip()
    qtile.c.layout.shuffle_down()
    assert qtile.c.layout.info()['main'] == 'two'
    assert qtile.c.layout.info()['secondary'] == ['three', 'focused', 'one']

    # Swap secondary down
    qtile.c.layout.swap_left()
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['three', 'two', 'one']

    # Swap main up
    qtile.c.layout.swap_right()
    assert qtile.c.layout.info()['main'] == 'three'
    assert qtile.c.layout.info()['secondary'] == ['focused', 'two', 'one']

    # Do swap main
    qtile.c.layout.swap_main()
    assert qtile.c.layout.info()['main'] == 'focused'
    assert qtile.c.layout.info()['secondary'] == ['three', 'two', 'one']


@monadtall_config
def test_tall_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("float1")
    qtile.c.window.toggle_floating()
    qtile.test_window("float2")
    qtile.c.window.toggle_floating()
    qtile.test_window("three")

    # test preconditions
    assert qtile.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assert_focused(qtile, "three")

    # starting from the last tiled client, we first cycle through floating ones,
    # and afterwards through the tiled
    assert_focus_path(qtile, 'float1', 'float2', 'one', 'two', 'three')


@monadwide_config
def test_wide_window_focus_cycle(qtile):
    # setup 3 tiled and two floating clients
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("float1")
    qtile.c.window.toggle_floating()
    qtile.test_window("float2")
    qtile.c.window.toggle_floating()
    qtile.test_window("three")

    # test preconditions
    assert qtile.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assert_focused(qtile, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(qtile, 'float1', 'float2', 'one', 'two', 'three')
