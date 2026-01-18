import random

import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.helpers import Retry


class GroupConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [layout.MonadTall()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


group_config = pytest.mark.parametrize("manager", [GroupConfig], indirect=True)


@group_config
def test_window_order(manager):
    # windows to add
    windows_name = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    windows = {}

    # Add windows one by one
    for win in windows_name:
        windows[win] = manager.test_window(win)

    # Windows must be sorted in the same order as they were created
    assert windows_name == manager.c.group.info()["windows"]

    # Randomly remove 5 windows and see if orders remains persistant
    for i in range(5):
        win_to_remove = random.choice(windows_name)
        windows_name.remove(win_to_remove)
        manager.kill_window(windows[win_to_remove])
        del windows[win_to_remove]
        assert windows_name == manager.c.group.info()["windows"]


@group_config
def test_focus_by_index(manager):
    manager.c.group["a"].toscreen()
    manager.test_window("one")
    manager.test_window("two")

    info = manager.c.group.info()
    assert info.get("focus") == "two"

    manager.c.group.focus_by_index(1)
    info = manager.c.group.info()
    assert info.get("focus") == "two"

    manager.c.group.focus_by_index(3)
    info = manager.c.group.info()
    assert info.get("focus") == "two"

    manager.c.group.focus_by_index(0)
    info = manager.c.group.info()
    assert info.get("focus") == "one"


@group_config
def test_toscreen_toggle(manager):
    assert manager.c.group.info()["name"] == "a"  # Start on "a"
    manager.c.group["b"].toscreen()
    assert manager.c.group.info()["name"] == "b"  # Switch to "b"
    manager.c.group["b"].toscreen()
    assert manager.c.group.info()["name"] == "b"  # Does not toggle by default
    manager.c.group["b"].toscreen(toggle=True)
    assert manager.c.group.info()["name"] == "a"  # Explicitly toggling moves to "a"
    manager.c.group["b"].toscreen(toggle=True)
    manager.c.group["b"].toscreen(toggle=True)
    assert manager.c.group.info()["name"] == "a"  # Toggling twice roundtrips between the two


class NoPersistGroupConfig(GroupConfig):
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b", exclusive=True),
        libqtile.config.Group("c", persist=False),
    ]


@pytest.mark.parametrize("manager", [NoPersistGroupConfig], indirect=True)
def test_non_persistent_groups(manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_removed(group_name):
        assert group_name not in manager.c.get_groups()

    window_name = "no_match"
    manager.c.group["b"].toscreen()
    manager.test_window(window_name)
    assert window_name not in manager.c.group.info()["windows"]  # Window was moved to a new group
    group_name = "TestWindow"  # The new group is named after the window's `wm_class` property
    assert group_name in manager.c.get_groups()
    manager.c.group[group_name].toscreen()
    assert manager.c.window.info()["name"] == window_name
    manager.c.window.togroup("a")
    wait_for_removed(group_name)

    window_name = "bar"
    manager.c.group["c"].toscreen()
    manager.test_window(window_name)
    assert manager.c.window.info()["name"] == window_name
    manager.c.window.togroup("a")
    wait_for_removed(group_name)
