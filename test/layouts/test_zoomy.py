import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused


class ZoomyConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [
        layout.Zoomy(columnwidth=200),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


zoomy_config = pytest.mark.parametrize("manager", [ZoomyConfig], indirect=True)


@zoomy_config
def test_zoomy_one(manager):
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 600, 600)
    manager.test_window("two")
    assert_dimensions(manager, 0, 0, 600, 600)
    manager.test_window("three")
    assert_dimensions(manager, 0, 0, 600, 600)
    assert_focus_path(manager, "two", "one", "three")
    # TODO(pc) find a way to check size of inactive windows


@zoomy_config
def test_zoomy_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions, Zoomy adds clients at head
    assert manager.c.layout.info()["clients"] == ["three", "two", "one"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "two", "one", "float1", "float2", "three")
