import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focused


class FloatingConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [layout.Floating()]
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


floating_config = pytest.mark.parametrize("manager", [FloatingConfig], indirect=True)


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
