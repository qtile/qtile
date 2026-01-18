import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused


class VerticalTileConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    # default border and margin
    layouts = [layout.VerticalTile(columns=2)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


class VerticalTileSingleBorderConfig(VerticalTileConfig):
    layouts = [layout.VerticalTile(columns=2, single_border_width=2, border_width=8)]


class VerticalTileSingleMarginConfig(VerticalTileConfig):
    layouts = [layout.VerticalTile(columns=2, single_margin=2, margin=8)]


verticaltile_config = pytest.mark.parametrize("manager", [VerticalTileConfig], indirect=True)
verticaltile_single_border_config = pytest.mark.parametrize(
    "manager", [VerticalTileSingleBorderConfig], indirect=True
)
verticaltile_single_margin_config = pytest.mark.parametrize(
    "manager", [VerticalTileSingleMarginConfig], indirect=True
)


@verticaltile_config
def test_verticaltile_simple(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 798, 598)
    manager.test_window("two")
    assert_dimensions(manager, 0, 300, 798, 298)
    manager.test_window("three")
    assert_dimensions(manager, 0, 400, 798, 198)


@verticaltile_config
def test_verticaltile_maximize(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 798, 598)
    manager.test_window("two")
    assert_dimensions(manager, 0, 300, 798, 298)
    # Maximize the bottom layout, taking 75% of space
    manager.c.layout.maximize()
    assert_dimensions(manager, 0, 150, 798, 448)


@verticaltile_config
def test_verticaltile_window_focus_cycle(manager):
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


@verticaltile_single_border_config
def test_verticaltile_single_border(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 796, 596)
    manager.test_window("two")
    assert_dimensions(manager, 0, 300, 784, 284)
    manager.test_window("three")
    assert_dimensions(manager, 0, 400, 784, 184)


@verticaltile_single_margin_config
def test_verticaltile_single_margin(manager):
    manager.test_window("one")
    assert_dimensions(manager, 2, 2, 794, 594)
    manager.test_window("two")
    assert_dimensions(manager, 8, 308, 782, 282)
    manager.test_window("three")
    assert_dimensions(manager, 8, 408, 782, 182)
