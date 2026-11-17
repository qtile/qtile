import pytest

import libqtile.config
from libqtile import layout
from libqtile.config import ScreenRect
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focused


class FloatingConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [layout.Floating()]
    floating_layout = layout.Floating(
        fullscreen_border_width=15,
        max_border_width=10,
    )
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


floating_config = pytest.mark.parametrize("manager", [FloatingConfig], indirect=True)


class _FakeWindowGeometry:
    """Just enough of a window for Floating.on_screen()."""

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


@pytest.mark.parametrize(
    "x, y",
    [
        (2559, 1200),  # left
        (2561, 1200),  # right
        (2560, 1199),  # top
        (2560, 1201),  # bottom
    ],
)
def test_on_screen_off_screen(x, y):
    floating = layout.Floating()
    # Landscape screen (width > height) with a non-zero origin so that checks
    # using the wrong dimension or ignoring the origin are caught
    screen = ScreenRect(2560, 1200, 2048, 1152)
    window = _FakeWindowGeometry(x, y, screen.width, screen.height)
    assert not floating.on_screen(window, screen)


def test_on_screen_aligned():
    floating = layout.Floating()
    screen = ScreenRect(2560, 1200, 2048, 1152)
    # A window the size of the screen is on screen only when exactly aligned
    window = _FakeWindowGeometry(screen.x, screen.y, screen.width, screen.height)
    assert floating.on_screen(window, screen)


@floating_config
def test_float_next_prev_window(manager):
    # spawn three windows
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    # focus previous windows
    assert_focused(manager, "three")
    manager.c.group.prev_window()
    assert_focused(manager, "two")
    manager.c.group.prev_window()
    assert_focused(manager, "one")
    # checking that it loops around properly
    manager.c.group.prev_window()
    assert_focused(manager, "three")

    # focus next windows
    # checking that it loops around properly
    manager.c.group.next_window()
    assert_focused(manager, "one")
    manager.c.group.next_window()
    assert_focused(manager, "two")
    manager.c.group.next_window()
    assert_focused(manager, "three")


@floating_config
def test_border_widths(manager):
    manager.test_window("one")

    # Default geometry
    info = manager.c.window.info()
    assert info["x"] == 350
    assert info["y"] == 250
    assert info["width"] == 100
    assert info["height"] == 100

    # Fullscreen
    manager.c.window.enable_fullscreen()
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == 770
    assert info["height"] == 570
    manager.c.window.disable_fullscreen()

    # Maximized
    manager.c.window.toggle_maximize()
    info = manager.c.window.info()
    assert info["x"] == 0
    assert info["y"] == 0
    assert info["width"] == 780
    assert info["height"] == 580
