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
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused


class MonadTallConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadTall()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadtall_config = pytest.mark.parametrize("manager", [MonadTallConfig], indirect=True)


class MonadTallNCPBeforeCurrentConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadTall(new_client_position="before_current")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadtallncpbeforecurrent_config = pytest.mark.parametrize(
    "manager", [MonadTallNCPBeforeCurrentConfig], indirect=True
)


class MonadTallNCPAfterCurrentConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadTall(new_client_position="after_current")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadtallncpaftercurrent_config = pytest.mark.parametrize(
    "manager", [MonadTallNCPAfterCurrentConfig], indirect=True
)


class MonadTallNewCLientPositionBottomConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadTall(new_client_position="bottom")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


class MonadTallMarginsConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadTall(margin=4)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadtallmargins_config = pytest.mark.parametrize(
    "manager", [MonadTallMarginsConfig], indirect=True
)


class MonadWideConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadWide()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadwide_config = pytest.mark.parametrize("manager", [MonadWideConfig], indirect=True)


class MonadWideNewClientPositionTopConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadWide(new_client_position="top")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


class MonadWideMarginsConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadWide(margin=4)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@monadtall_config
def test_tall_add_clients(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two"]
    assert_focused(manager, "two")

    manager.test_window("three")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three"]
    assert_focused(manager, "three")

    manager.c.layout.previous()
    assert_focused(manager, "two")

    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "four", "three"]
    assert_focused(manager, "four")


@monadtallncpbeforecurrent_config
def test_tall_add_clients_before_current(manager):
    """Test add client with new_client_position = before_current."""
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["two", "one"]
    manager.c.layout.next()
    assert_focused(manager, "two")
    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["four", "two", "one"]
    assert_focused(manager, "four")


@monadtallncpaftercurrent_config
def test_tall_add_clients_after_current(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    assert_focused(manager, "two")
    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "four", "three"]
    assert_focused(manager, "four")


@pytest.mark.parametrize("manager", [MonadTallNewCLientPositionBottomConfig], indirect=True)
def test_tall_add_clients_at_bottom(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    assert_focused(manager, "two")
    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "four"]


@monadwide_config
def test_wide_add_clients(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two"]
    assert_focused(manager, "two")

    manager.test_window("three")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three"]
    assert_focused(manager, "three")

    manager.c.layout.previous()
    assert_focused(manager, "two")

    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "four", "three"]
    assert_focused(manager, "four")


@pytest.mark.parametrize("manager", [MonadWideNewClientPositionTopConfig], indirect=True)
def test_wide_add_clients_new_client_postion_top(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == ["one"]
    assert_focused(manager, "two")

    manager.test_window("three")
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["two", "one"]
    assert_focused(manager, "three")

    manager.c.layout.next()
    assert_focused(manager, "two")

    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]
    assert_focused(manager, "four")


@monadtallmargins_config
def test_tall_margins(manager):
    manager.test_window("one")
    assert_dimensions(manager, 4, 4, 788, 588)

    manager.test_window("two")
    assert_focused(manager, "two")
    assert_dimensions(manager, 404, 4, 388, 588)

    manager.c.layout.previous()
    assert_focused(manager, "one")
    assert_dimensions(manager, 4, 4, 392, 588)


@pytest.mark.parametrize("manager", [MonadWideMarginsConfig], indirect=True)
def test_wide_margins(manager):
    manager.test_window("one")
    assert_dimensions(manager, 4, 4, 788, 588)

    manager.test_window("two")
    assert_focused(manager, "two")
    assert_dimensions(manager, 4, 304, 788, 288)

    manager.c.layout.previous()
    assert_focused(manager, "one")
    assert_dimensions(manager, 4, 4, 788, 292)


@monadtall_config
def test_tall_growmain_solosecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.c.layout.previous()
    assert_focused(manager, "one")

    assert_dimensions(manager, 0, 0, 396, 596)
    manager.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(manager, 0, 0, 436, 596)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_solosecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.c.layout.previous()
    assert_focused(manager, "one")

    assert_dimensions(manager, 0, 0, 796, 296)
    manager.c.layout.grow()
    # Grows 5% of 800 = 30 pixels
    assert_dimensions(manager, 0, 0, 796, 326)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 796, 146)


@monadtall_config
def test_tall_growmain_multiplesecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    manager.c.layout.previous()
    assert_focused(manager, "one")

    assert_dimensions(manager, 0, 0, 396, 596)
    manager.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(manager, 0, 0, 436, 596)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 196, 596)


@monadwide_config
def test_wide_growmain_multiplesecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    manager.c.layout.previous()
    assert_focused(manager, "one")

    assert_dimensions(manager, 0, 0, 796, 296)
    manager.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(manager, 0, 0, 796, 326)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 0, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 0, 796, 146)


@monadtall_config
def test_tall_growsecondary_solosecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    assert_focused(manager, "two")

    assert_dimensions(manager, 400, 0, 396, 596)
    manager.c.layout.grow()
    # Grows 5% of 800 = 40 pixels
    assert_dimensions(manager, 360, 0, 436, 596)
    manager.c.layout.shrink()
    assert_dimensions(manager, 400, 0, 396, 596)

    # Max width is 75% of 800 = 600 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 200, 0, 596, 596)

    # Min width is 25% of 800 = 200 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 600, 0, 196, 596)


@monadwide_config
def test_wide_growsecondary_solosecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    assert_focused(manager, "two")

    assert_dimensions(manager, 0, 300, 796, 296)
    manager.c.layout.grow()
    # Grows 5% of 600 = 30 pixels
    assert_dimensions(manager, 0, 270, 796, 326)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 300, 796, 296)

    # Max width is 75% of 600 = 450 pixels
    for _ in range(10):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 150, 796, 446)

    # Min width is 25% of 600 = 150 pixels
    for _ in range(10):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 450, 796, 146)


@monadtall_config
def test_tall_growsecondary_multiplesecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    assert_focused(manager, "two")

    assert_dimensions(manager, 400, 0, 396, 296)
    # Grow 20 pixels
    manager.c.layout.grow()
    assert_dimensions(manager, 400, 0, 396, 316)
    manager.c.layout.shrink()
    assert_dimensions(manager, 400, 0, 396, 296)

    # Min height of other is 85 pixels, leaving 515
    for _ in range(20):
        manager.c.layout.grow()
    assert_dimensions(manager, 400, 0, 396, 511)

    # Min height of manager is 85 pixels
    for _ in range(40):
        manager.c.layout.shrink()
    assert_dimensions(manager, 400, 0, 396, 85)


@monadwide_config
def test_wide_growsecondary_multiplesecondary(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    manager.test_window("three")
    manager.c.layout.previous()
    assert_focused(manager, "two")

    assert_dimensions(manager, 0, 300, 396, 296)
    # Grow 20 pixels
    manager.c.layout.grow()
    assert_dimensions(manager, 0, 300, 416, 296)
    manager.c.layout.shrink()
    assert_dimensions(manager, 0, 300, 396, 296)

    # Min width of other is 85 pixels, leaving 715
    for _ in range(20):
        manager.c.layout.grow()
    assert_dimensions(manager, 0, 300, 710, 296)  # TODO why not 711 ?

    # Min width of manager is 85 pixels
    for _ in range(40):
        manager.c.layout.shrink()
    assert_dimensions(manager, 0, 300, 85, 296)


@monadtall_config
def test_tall_flip(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    # Check all the dimensions
    manager.c.layout.next()
    assert_focused(manager, "one")
    assert_dimensions(manager, 0, 0, 396, 596)

    manager.c.layout.next()
    assert_focused(manager, "two")
    assert_dimensions(manager, 400, 0, 396, 296)

    manager.c.layout.next()
    assert_focused(manager, "three")
    assert_dimensions(manager, 400, 300, 396, 296)

    # Now flip it and do it again
    manager.c.layout.flip()

    manager.c.layout.next()
    assert_focused(manager, "one")
    assert_dimensions(manager, 400, 0, 396, 596)

    manager.c.layout.next()
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 0, 396, 296)

    manager.c.layout.next()
    assert_focused(manager, "three")
    assert_dimensions(manager, 0, 300, 396, 296)


@monadwide_config
def test_wide_flip(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    # Check all the dimensions
    manager.c.layout.next()
    assert_focused(manager, "one")
    assert_dimensions(manager, 0, 0, 796, 296)

    manager.c.layout.next()
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 300, 396, 296)

    manager.c.layout.next()
    assert_focused(manager, "three")
    assert_dimensions(manager, 400, 300, 396, 296)

    # Now flip it and do it again
    manager.c.layout.flip()

    manager.c.layout.next()
    assert_focused(manager, "one")
    assert_dimensions(manager, 0, 300, 796, 296)

    manager.c.layout.next()
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 0, 396, 296)

    manager.c.layout.next()
    assert_focused(manager, "three")
    assert_dimensions(manager, 400, 0, 396, 296)


@monadtall_config
def test_tall_set_and_reset(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    assert_focused(manager, "two")
    assert_dimensions(manager, 400, 0, 396, 596)

    manager.c.layout.set_ratio(0.75)
    assert_focused(manager, "two")
    assert_dimensions(manager, 600, 0, 196, 596)

    manager.c.layout.set_ratio(0.25)
    assert_focused(manager, "two")
    assert_dimensions(manager, 200, 0, 596, 596)

    manager.c.layout.reset()
    assert_focused(manager, "two")
    assert_dimensions(manager, 400, 0, 396, 596)


@monadwide_config
def test_wide_set_and_reset(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)

    manager.test_window("two")
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 300, 796, 296)

    manager.c.layout.set_ratio(0.75)
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 450, 796, 146)

    manager.c.layout.set_ratio(0.25)
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 150, 796, 446)

    manager.c.layout.reset()
    assert_focused(manager, "two")
    assert_dimensions(manager, 0, 300, 796, 296)


@monadtall_config
def test_tall_shuffle(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")

    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "four"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "four", "three"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["four", "two", "three"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == ["one", "two", "three"]


@monadwide_config
def test_wide_shuffle(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")

    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "four"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "four", "three"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["four", "two", "three"]

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == ["one", "two", "three"]


@monadtall_config
def test_tall_swap(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("focused")

    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "focused"]

    # Swap a secondary left, left aligned
    manager.c.layout.swap_left()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "one"]

    # Swap a main right, left aligned
    manager.c.layout.swap_right()
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == ["focused", "three", "one"]

    # flip over
    manager.c.layout.flip()
    manager.c.layout.shuffle_down()
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == ["three", "focused", "one"]

    # Swap secondary right, right aligned
    manager.c.layout.swap_right()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Swap main left, right aligned
    manager.c.layout.swap_left()
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["focused", "two", "one"]

    # Do swap main
    manager.c.layout.swap_main()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Since the focused window is already to the right this swap shouldn't
    # change the position of the windows
    # The swap function will try to get all windows to the right of the
    # focused window, which will result in a empty list that could cause
    # an error if not handled

    # Swap againts right edge
    manager.c.layout.swap_right()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Same as above but for the swap_left function

    # Swap againts left edge
    manager.c.layout.swap_left()
    manager.c.layout.swap_left()
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["focused", "two", "one"]


@monadwide_config
def test_wide_swap(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("focused")

    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "focused"]

    # Swap a secondary up
    manager.c.layout.swap_right()  # equivalent to swap_down
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["two", "three", "one"]

    # Swap a main down
    manager.c.layout.swap_left()  # equivalent to swap up
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == ["focused", "three", "one"]

    # flip over
    manager.c.layout.flip()
    manager.c.layout.shuffle_down()
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == ["three", "focused", "one"]

    # Swap secondary down
    manager.c.layout.swap_left()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Swap main up
    manager.c.layout.swap_right()
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["focused", "two", "one"]

    # Do swap main
    manager.c.layout.swap_main()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Since the focused window is already to the left this swap shouldn't
    # change the position of the windows
    # The swap function will try to get all windows to the left of the
    # focused window, which will result in a empty list that could cause
    # an error if not handled

    # Swap againts left edge
    manager.c.layout.swap_left()
    assert manager.c.layout.info()["main"] == "focused"
    assert manager.c.layout.info()["secondary"] == ["three", "two", "one"]

    # Same as above but for the swap_right function

    # Swap againts right edge
    manager.c.layout.swap_right()
    manager.c.layout.swap_right()
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == ["focused", "two", "one"]


@monadtall_config
def test_tall_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions
    assert manager.c.layout.info()["clients"] == ["one", "two", "three"]
    # last added window has focus
    assert_focused(manager, "three")

    # starting from the last tiled client, we first cycle through floating ones,
    # and afterwards through the tiled
    assert_focus_path(manager, "float1", "float2", "one", "two", "three")


@monadwide_config
def test_wide_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions
    assert manager.c.layout.info()["clients"] == ["one", "two", "three"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "float1", "float2", "one", "two", "three")


# MonadThreeCol
class MonadThreeColConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.MonadThreeCol()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


monadthreecol_config = pytest.mark.parametrize("manager", [MonadThreeColConfig], indirect=True)


@monadthreecol_config
def test_three_col_add_clients(manager):
    manager.test_window("one")
    assert manager.c.layout.info()["main"] == "one"
    assert manager.c.layout.info()["secondary"] == dict(left=[], right=[])

    manager.test_window("two")
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == dict(left=["one"], right=[])
    assert_focused(manager, "two")

    manager.test_window("three")
    assert manager.c.layout.info()["main"] == "three"
    assert manager.c.layout.info()["secondary"] == dict(left=["two"], right=["one"])
    assert_focused(manager, "three")

    manager.test_window("four")
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == dict(left=["three", "two"], right=["one"])
    assert_focused(manager, "four")

    manager.test_window("five")
    assert manager.c.layout.info()["main"] == "five"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["two", "one"]
    )
    assert_focused(manager, "five")

    manager.c.layout.next()
    assert_focused(manager, "four")
    manager.c.layout.next()
    assert_focused(manager, "three")
    manager.c.layout.next()
    assert_focused(manager, "two")
    manager.c.layout.next()
    assert_focused(manager, "one")


@monadthreecol_config
def test_three_col_shuffle(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")
    manager.test_window("five")

    manager.c.layout.shuffle_right()
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["five", "one"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_down()
    assert manager.c.layout.info()["main"] == "two"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["one", "five"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_left()
    assert manager.c.layout.info()["main"] == "five"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["one", "two"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_left()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["five", "three"], right=["one", "two"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_down()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["three", "five"], right=["one", "two"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_up()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["five", "three"], right=["one", "two"]
    )
    assert_focused(manager, "five")

    manager.c.layout.shuffle_right()
    assert manager.c.layout.info()["main"] == "five"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["one", "two"]
    )
    assert_focused(manager, "five")


@monadthreecol_config
def test_three_col_swap_main(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")
    manager.test_window("five")

    manager.c.layout.next()
    manager.c.layout.swap_main()
    assert manager.c.layout.info()["main"] == "four"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["five", "three"], right=["two", "one"]
    )
    assert_focused(manager, "four")

    manager.c.layout.next()
    manager.c.layout.swap_main()
    assert manager.c.layout.info()["main"] == "five"
    assert manager.c.layout.info()["secondary"] == dict(
        left=["four", "three"], right=["two", "one"]
    )
    assert_focused(manager, "five")
