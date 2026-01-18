import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focus_path, assert_focused


class StackConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        layout.Stack(num_stacks=2),
        layout.Stack(num_stacks=1),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


stack_config = pytest.mark.parametrize("manager", [StackConfig], indirect=True)


def _stacks(manager):
    stacks = []
    for i in manager.c.layout.info()["stacks"]:
        windows = i["clients"]
        current = i["current"]
        stacks.append(windows[current:] + windows[:current])
    return stacks


@stack_config
def test_stack_commands(manager):
    assert manager.c.layout.info()["current_stack"] == 0
    manager.test_window("one")
    assert _stacks(manager) == [["one"], []]
    assert manager.c.layout.info()["current_stack"] == 0
    manager.test_window("two")
    assert _stacks(manager) == [["one"], ["two"]]
    assert manager.c.layout.info()["current_stack"] == 1
    manager.test_window("three")
    assert _stacks(manager) == [["one"], ["three", "two"]]
    assert manager.c.layout.info()["current_stack"] == 1

    manager.c.layout.delete()
    assert _stacks(manager) == [["one", "three", "two"]]
    info = manager.c.get_groups()["a"]
    assert info["focus"] == "one"
    manager.c.layout.delete()
    assert len(_stacks(manager)) == 1

    manager.c.layout.add()
    assert _stacks(manager) == [["one", "three", "two"], []]

    manager.c.layout.rotate()
    assert _stacks(manager) == [[], ["one", "three", "two"]]


@stack_config
def test_stack_down(manager):
    manager.c.layout.down()


@stack_config
def test_stack_addremove(manager):
    one = manager.test_window("one")
    manager.c.layout.next()
    two = manager.test_window("two")
    three = manager.test_window("three")
    assert _stacks(manager) == [["one"], ["three", "two"]]
    assert manager.c.layout.info()["current_stack"] == 1
    manager.kill_window(three)
    assert manager.c.layout.info()["current_stack"] == 1
    manager.kill_window(two)
    assert manager.c.layout.info()["current_stack"] == 0
    manager.c.layout.next()
    two = manager.test_window("two")
    manager.c.layout.next()
    assert manager.c.layout.info()["current_stack"] == 0
    manager.kill_window(one)
    assert manager.c.layout.info()["current_stack"] == 1


@stack_config
def test_stack_rotation(manager):
    manager.c.layout.delete()
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    assert _stacks(manager) == [["three", "two", "one"]]
    manager.c.layout.down()
    assert _stacks(manager) == [["two", "one", "three"]]
    manager.c.layout.up()
    assert _stacks(manager) == [["three", "two", "one"]]
    manager.c.layout.down()
    manager.c.layout.down()
    assert _stacks(manager) == [["one", "three", "two"]]


@stack_config
def test_stack_nextprev(manager):
    manager.c.layout.add()
    one = manager.test_window("one")
    two = manager.test_window("two")
    three = manager.test_window("three")

    assert manager.c.get_groups()["a"]["focus"] == "three"
    manager.c.layout.next()
    assert manager.c.get_groups()["a"]["focus"] == "one"

    manager.c.layout.previous()
    assert manager.c.get_groups()["a"]["focus"] == "three"
    manager.c.layout.previous()
    assert manager.c.get_groups()["a"]["focus"] == "two"

    manager.c.layout.next()
    manager.c.layout.next()
    manager.c.layout.next()
    assert manager.c.get_groups()["a"]["focus"] == "two"

    manager.kill_window(three)
    manager.c.layout.next()
    assert manager.c.get_groups()["a"]["focus"] == "one"
    manager.c.layout.previous()
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.layout.next()
    manager.kill_window(two)
    manager.c.layout.next()
    assert manager.c.get_groups()["a"]["focus"] == "one"

    manager.kill_window(one)
    manager.c.layout.next()
    assert manager.c.get_groups()["a"]["focus"] is None
    manager.c.layout.previous()
    assert manager.c.get_groups()["a"]["focus"] is None


@stack_config
def test_stack_window_removal(manager):
    manager.c.layout.next()
    manager.test_window("one")
    two = manager.test_window("two")
    manager.c.layout.down()
    manager.kill_window(two)


@stack_config
def test_stack_split(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    stacks = manager.c.layout.info()["stacks"]
    assert not stacks[1]["split"]
    manager.c.layout.toggle_split()
    stacks = manager.c.layout.info()["stacks"]
    assert stacks[1]["split"]


@stack_config
def test_stack_shuffle(manager):
    manager.c.next_layout()
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")

    stack = manager.c.layout.info()["stacks"][0]
    assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        manager.c.layout.shuffle_up()
        stack = manager.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"
    for i in range(5):
        manager.c.layout.shuffle_down()
        stack = manager.c.layout.info()["stacks"][0]
        assert stack["clients"][stack["current"]] == "three"


@stack_config
def test_stack_client_to(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["stacks"][0]["clients"] == ["one"]
    manager.c.layout.client_to_previous()
    assert manager.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]
    manager.c.layout.client_to_previous()
    assert manager.c.layout.info()["stacks"][0]["clients"] == ["one"]
    assert manager.c.layout.info()["stacks"][1]["clients"] == ["two"]
    manager.c.layout.client_to_next()
    assert manager.c.layout.info()["stacks"][0]["clients"] == ["two", "one"]


@stack_config
def test_stack_info(manager):
    manager.test_window("one")
    assert manager.c.layout.info()["stacks"]


@stack_config
def test_stack_window_focus_cycle(manager):
    # setup 3 tiled and two floating clients
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("float1")
    manager.c.window.toggle_floating()
    manager.test_window("float2")
    manager.c.window.toggle_floating()
    manager.test_window("three")

    # test preconditions, stack adds clients at pos of current
    assert manager.c.layout.info()["clients"] == ["three", "one", "two"]
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "one", "two", "float1", "float2", "three")
