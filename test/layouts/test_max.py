import pytest

import libqtile.config
import libqtile.resources.default_config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focus_path, assert_focused


class MaxConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        layout.Max(),
        layout.Max(margin=5),
        layout.Max(margin=5, border_width=5),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


max_config = pytest.mark.parametrize("manager", [MaxConfig], indirect=True)


class MaxLayeredConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [layout.Max(only_focused=False)]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


maxlayered_config = pytest.mark.parametrize("manager", [MaxLayeredConfig], indirect=True)


def assert_z_stack(manager, windows):
    if manager.backend.name != "x11":
        # TODO: Test wayland backend when proper Z-axis is implemented there
        return
    stack = manager.backend.get_all_windows()
    wins = [(w["name"], stack.index(w["id"])) for w in manager.c.windows()]
    wins.sort(key=lambda x: x[1])
    assert [x[0] for x in wins] == windows


@max_config
def test_max_simple(manager):
    manager.test_window("one")
    assert manager.c.layout.info()["clients"] == ["one"]
    assert_z_stack(manager, ["one"])
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["one", "two"]
    assert_z_stack(manager, ["one", "two"])


@maxlayered_config
def test_max_layered(manager):
    manager.test_window("one")
    assert manager.c.layout.info()["clients"] == ["one"]
    assert_z_stack(manager, ["one"])
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["one", "two"]
    assert_z_stack(manager, ["one", "two"])


@max_config
def test_max_updown(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    assert manager.c.layout.info()["clients"] == ["one", "two", "three"]
    assert_z_stack(manager, ["one", "two", "three"])
    manager.c.layout.up()
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.layout.down()
    assert manager.c.get_groups()["a"]["focus"] == "three"
    assert_z_stack(manager, ["one", "two", "three"])
    manager.c.layout.down()
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert_z_stack(manager, ["one", "two", "three"])


@maxlayered_config
def test_layered_max_updown(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    assert manager.c.layout.info()["clients"] == ["one", "two", "three"]
    assert_z_stack(manager, ["one", "two", "three"])
    manager.c.layout.up()
    assert manager.c.get_groups()["a"]["focus"] == "two"
    assert_z_stack(manager, ["one", "three", "two"])
    manager.c.layout.up()
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert_z_stack(manager, ["three", "two", "one"])
    manager.c.layout.down()
    assert manager.c.get_groups()["a"]["focus"] == "two"
    assert_z_stack(manager, ["three", "one", "two"])
    manager.c.layout.down()
    assert manager.c.get_groups()["a"]["focus"] == "three"
    assert_z_stack(manager, ["one", "two", "three"])


@pytest.mark.parametrize("manager", [MaxConfig, MaxLayeredConfig], indirect=True)
def test_max_remove(manager):
    manager.test_window("one")
    two = manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["one", "two"]
    assert_z_stack(manager, ["one", "two"])
    manager.kill_window(two)
    assert manager.c.layout.info()["clients"] == ["one"]
    assert_z_stack(manager, ["one"])


@max_config
def test_max_window_focus_cycle(manager):
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

    # Floats are kept above in stacking order
    assert_z_stack(manager, ["one", "two", "three", "float1", "float2"])
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "float1", "float2", "one", "two", "three")


@maxlayered_config
def test_layered_max_window_focus_cycle(manager):
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

    # Floats kept above by default
    assert_z_stack(manager, ["one", "two", "three", "float1", "float2"])
    # last added window has focus
    assert_focused(manager, "three")

    # assert window focus cycle, according to order in layout
    assert_focus_path(manager, "float1", "float2", "one", "two", "three")


@max_config
def test_max_window_margins_and_borders(manager):
    def parse_margin(margin):
        if isinstance(margin, int):
            return (margin,) * 4
        return margin

    manager.test_window("one")
    screen = manager.c.group["a"].screen.info()
    for _layout in MaxConfig.layouts:
        window = manager.c.window.info()
        margin = parse_margin(_layout.margin)
        border = _layout.border_width

        assert screen["width"] == window["width"] + margin[0] + margin[2] + border * 2
        assert screen["height"] == window["height"] + margin[1] + margin[3] + border * 2
        manager.c.next_layout()
