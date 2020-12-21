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

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.conftest import no_xinerama
from test.layouts.layout_utils import (
    assert_dimensions,
    assert_focus_path,
    assert_focused,
)


class MonadTallConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadTall()
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadtall_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MonadTallConfig], indirect=True)(x))


class MonadTallMarginsConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadTall(margin=4)
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadtallmargins_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MonadTallMarginsConfig], indirect=True)(x))


class MonadWideConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadWide()
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadwide_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MonadWideConfig], indirect=True)(x))


class MonadWideMarginsConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        layout.MonadWide(margin=4)
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def monadwidemargins_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [MonadWideMarginsConfig], indirect=True)(x))


@monadtall_config
def test_tall_add_clients(self):
    self.test_window('one')
    self.test_window('two')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two']
    assert_focused(self, 'two')

    self.test_window('three')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'three']
    assert_focused(self, 'three')

    self.c.layout.previous()
    assert_focused(self, 'two')

    self.test_window('four')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assert_focused(self, 'four')


@monadwide_config
def test_wide_add_clients(self):
    self.test_window('one')
    self.test_window('two')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two']
    assert_focused(self, 'two')

    self.test_window('three')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'three']
    assert_focused(self, 'three')

    self.c.layout.previous()
    assert_focused(self, 'two')

    self.test_window('four')
    assert self.c.layout.info()["main"] == 'one'
    assert self.c.layout.info()["secondary"] == ['two', 'four', 'three']
    assert_focused(self, 'four')


@monadtallmargins_config
def test_tall_margins(self):
    self.test_window('one')
    assert_dimensions(self, 4, 4, 788, 588)

    self.test_window('two')
    assert_focused(self, 'two')
    assert_dimensions(self, 404, 4, 388, 588)

    self.c.layout.previous()
    assert_focused(self, 'one')
    assert_dimensions(self, 4, 4, 392, 588)


@monadwidemargins_config
def test_wide_margins(self):
    self.test_window('one')
    assert_dimensions(self, 4, 4, 788, 588)

    self.test_window('two')
    assert_focused(self, 'two')
    assert_dimensions(self, 4, 304, 788, 288)

    self.c.layout.previous()
    assert_focused(self, 'one')
    assert_dimensions(self, 4, 4, 788, 292)


@monadtall_config
def test_tall_growmain_solosecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.c.layout.previous()
    assert_focused(self, 'one')

    assert_dimensions(self, 0, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(self, 0, 0, 436, 596)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_solosecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.c.layout.previous()
    assert_focused(self, 'one')

    assert_dimensions(self, 0, 0, 796, 296)
    self.c.layout.grow()
    # Grows 5% of 800 = 30 pixels
    assert_dimensions(self, 0, 0, 796, 326)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 796, 146)


@monadtall_config
def test_tall_growmain_multiplesecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.test_window('three')
    self.c.layout.previous()
    self.c.layout.previous()
    assert_focused(self, 'one')

    assert_dimensions(self, 0, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(self, 0, 0, 436, 596)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_multiplesecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.test_window('three')
    self.c.layout.previous()
    self.c.layout.previous()
    assert_focused(self, 'one')

    assert_dimensions(self, 0, 0, 796, 296)
    self.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(self, 0, 0, 796, 326)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 0, 796, 146)


@monadtall_config
def test_tall_growsecondary_solosecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    assert_focused(self, 'two')

    assert_dimensions(self, 400, 0, 396, 596)
    self.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(self, 360, 0, 436, 596)
    self.c.layout.shrink()
    assert_dimensions(self, 400, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 200, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 600, 0, 196, 596)


@monadwide_config
def test_wide_growsecondary_solosecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    assert_focused(self, 'two')

    assert_dimensions(self, 0, 300, 796, 296)
    self.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(self, 0, 270, 796, 326)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 300, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        self.c.layout.grow()
    assert_dimensions(self, 0, 150, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 450, 796, 146)


@monadtall_config
def test_tall_growsecondary_multiplesecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.test_window('three')
    self.c.layout.previous()
    assert_focused(self, 'two')

    assert_dimensions(self, 400, 0, 396, 296)
    # Grow 20 pixels
    self.c.layout.grow()
    assert_dimensions(self, 400, 0, 396, 316)
    self.c.layout.shrink()
    assert_dimensions(self, 400, 0, 396, 296)

    # Min height of other is 85 pixels, leaving 515
    for _ in range(20):
        self.c.layout.grow()
    assert_dimensions(self, 400, 0, 396, 511)

    # Min height of self is 85 pixels
    for _ in range(40):
        self.c.layout.shrink()
    assert_dimensions(self, 400, 0, 396, 85)


@monadwide_config
def test_wide_growsecondary_multiplesecondary(self):
    self.test_window('one')
    assert_dimensions(self, 0, 0, 796, 596)

    self.test_window('two')
    self.test_window('three')
    self.c.layout.previous()
    assert_focused(self, 'two')

    assert_dimensions(self, 0, 300, 396, 296)
    # Grow 20 pixels
    self.c.layout.grow()
    assert_dimensions(self, 0, 300, 416, 296)
    self.c.layout.shrink()
    assert_dimensions(self, 0, 300, 396, 296)

    # Min width of other is 85 pixels, leaving 715
    for _ in range(20):
        self.c.layout.grow()
    assert_dimensions(self, 0, 300, 710, 296)  # TODO why not 711 ?

    # Min width of self is 85 pixels
    for _ in range(40):
        self.c.layout.shrink()
    assert_dimensions(self, 0, 300, 85, 296)


@monadtall_config
def test_tall_flip(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')

    # Check all the dimensions
    self.c.layout.next()
    assert_focused(self, 'one')
    assert_dimensions(self, 0, 0, 396, 596)

    self.c.layout.next()
    assert_focused(self, 'two')
    assert_dimensions(self, 400, 0, 396, 296)

    self.c.layout.next()
    assert_focused(self, 'three')
    assert_dimensions(self, 400, 300, 396, 296)

    # Now flip it and do it again
    self.c.layout.flip()

    self.c.layout.next()
    assert_focused(self, 'one')
    assert_dimensions(self, 400, 0, 396, 596)

    self.c.layout.next()
    assert_focused(self, 'two')
    assert_dimensions(self, 0, 0, 396, 296)

    self.c.layout.next()
    assert_focused(self, 'three')
    assert_dimensions(self, 0, 300, 396, 296)


@monadwide_config
def test_wide_flip(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')

    # Check all the dimensions
    self.c.layout.next()
    assert_focused(self, 'one')
    assert_dimensions(self, 0, 0, 796, 296)

    self.c.layout.next()
    assert_focused(self, 'two')
    assert_dimensions(self, 0, 300, 396, 296)

    self.c.layout.next()
    assert_focused(self, 'three')
    assert_dimensions(self, 400, 300, 396, 296)

    # Now flip it and do it again
    self.c.layout.flip()

    self.c.layout.next()
    assert_focused(self, 'one')
    assert_dimensions(self, 0, 300, 796, 296)

    self.c.layout.next()
    assert_focused(self, 'two')
    assert_dimensions(self, 0, 0, 396, 296)

    self.c.layout.next()
    assert_focused(self, 'three')
    assert_dimensions(self, 400, 0, 396, 296)


@monadtall_config
def test_tall_shuffle(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')
    self.test_window('four')

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


@monadwide_config
def test_wide_shuffle(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')
    self.test_window('four')

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


@monadtall_config
def test_tall_swap(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')
    self.test_window('focused')

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


@monadwide_config
def test_wide_swap(self):
    self.test_window('one')
    self.test_window('two')
    self.test_window('three')
    self.test_window('focused')

    assert self.c.layout.info()['main'] == 'one'
    assert self.c.layout.info()['secondary'] == ['two', 'three', 'focused']

    # Swap a secondary up
    self.c.layout.swap_right()  # equivalent to swap_down
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['two', 'three', 'one']

    # Swap a main down
    self.c.layout.swap_left()  # equivalent to swap up
    assert self.c.layout.info()['main'] == 'two'
    assert self.c.layout.info()['secondary'] == ['focused', 'three', 'one']

    # flip over
    self.c.layout.flip()
    self.c.layout.shuffle_down()
    assert self.c.layout.info()['main'] == 'two'
    assert self.c.layout.info()['secondary'] == ['three', 'focused', 'one']

    # Swap secondary down
    self.c.layout.swap_left()
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['three', 'two', 'one']

    # Swap main up
    self.c.layout.swap_right()
    assert self.c.layout.info()['main'] == 'three'
    assert self.c.layout.info()['secondary'] == ['focused', 'two', 'one']

    # Do swap main
    self.c.layout.swap_main()
    assert self.c.layout.info()['main'] == 'focused'
    assert self.c.layout.info()['secondary'] == ['three', 'two', 'one']


@monadtall_config
def test_tall_window_focus_cycle(self):
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_window("float1")
    self.c.window.toggle_floating()
    self.test_window("float2")
    self.c.window.toggle_floating()
    self.test_window("three")

    # test preconditions
    assert self.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assert_focused(self, "three")

    # starting from the last tiled client, we first cycle through floating ones,
    # and afterwards through the tiled
    assert_focus_path(self, 'float1', 'float2', 'one', 'two', 'three')


@monadwide_config
def test_wide_window_focus_cycle(self):
    # setup 3 tiled and two floating clients
    self.test_window("one")
    self.test_window("two")
    self.test_window("float1")
    self.c.window.toggle_floating()
    self.test_window("float2")
    self.c.window.toggle_floating()
    self.test_window("three")

    # test preconditions
    assert self.c.layout.info()['clients'] == ['one', 'two', 'three']
    # last added window has focus
    assert_focused(self, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(self, 'float1', 'float2', 'one', 'two', 'three')
