import pytest

import libqtile.config
from libqtile import bar, layout, widget
from libqtile.config import Screen
from libqtile.confreader import Config


class FakeScreenConfig(Config):
    auto_fullscreen = True
    floating_layout = layout.Floating()
    groups = [
        libqtile.config.Group(
            "a",
            layouts=[floating_layout],
        ),
        libqtile.config.Group("b"),
    ]
    layouts = [
        layout.Tile(),
    ]
    keys = []
    mouse = []
    fake_screens = [
        Screen(
            top=bar.Bar(
                [widget.GroupBox(), widget.WindowName(), widget.Clock()],
                10,
            ),
            width=1920,
            height=1080,
        ),
    ]
    screens = []


fakescreen_config = pytest.mark.parametrize("manager", [FakeScreenConfig], indirect=True)


@fakescreen_config
def test_maximize(manager):
    """Ensure that maximize saves and restores geometry"""
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["width"] == 1920
    assert manager.c.window.info()["height"] == 1070
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 10
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"


@fakescreen_config
def test_fullscreen(manager):
    """Ensure that fullscreen saves and restores geometry"""
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["width"] == 1920
    assert manager.c.window.info()["height"] == 1080
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["group"] == "a"

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["width"] == 1280
    assert manager.c.window.info()["height"] == 720
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"


@fakescreen_config
def test_fullscreen_restore_tiling(manager):
    """Ensure window is restored to tiling"""

    def window(name):
        for win in manager.c.windows():
            if win["name"] == name:
                return manager.c.window[win["id"]]
        assert False, f"Cannot find window: {name}"

    def is_floating(name):
        return window(name).info()["floating"]

    def is_tiled(name):
        return not is_floating(name)

    def is_fullscreen(name):
        return window(name).info()["fullscreen"]

    def assert_geometry(name, x, y, w, h):
        win = window(name)
        info = win.info()
        assert (x, y, w, h) == (info["x"], info["y"], info["width"], info["height"])

    manager.c.group["b"].toscreen()

    manager.test_window("one")
    manager.test_window("two")

    for win in ["one", "two"]:
        assert is_tiled(win)
        assert not is_fullscreen(win)

    # Check window one's tiled geometry
    assert_geometry("one", 1186, 10, 732, 1068)

    # Fullscreen
    window("one").toggle_fullscreen()
    assert is_fullscreen("one")
    assert not is_tiled("one")
    assert_geometry("one", 0, 0, 1920, 1080)

    # Revert to tiled
    window("one").toggle_fullscreen()
    assert not is_fullscreen("one")
    assert is_tiled("one")
    assert_geometry("one", 1186, 10, 732, 1068)


@fakescreen_config
def test_fullscreen_restore_floating(manager):
    """A floating window stays floating after leaving fullscreen

    See https://github.com/qtile/qtile/issues/5950
    """
    manager.c.group["b"].toscreen()
    manager.test_window("one")
    manager.test_window("two")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["floating"]

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["fullscreen"]
    assert manager.c.window.info()["width"] == 1920
    assert manager.c.window.info()["height"] == 1080

    manager.c.window.toggle_fullscreen()
    info = manager.c.window.info()
    assert not info["fullscreen"]
    assert info["floating"]
    assert (info["x"], info["y"], info["width"], info["height"]) == (50, 20, 1280, 720)


@fakescreen_config
def test_maximize_restore_floating(manager):
    """A floating window stays floating after leaving maximize"""
    manager.c.group["b"].toscreen()
    manager.test_window("one")
    manager.test_window("two")
    manager.c.window.set_position_floating(50, 20)
    manager.c.window.set_size_floating(1280, 720)
    assert manager.c.window.info()["floating"]

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["maximized"]

    manager.c.window.toggle_maximize()
    info = manager.c.window.info()
    assert not info["maximized"]
    assert info["floating"]
    assert (info["x"], info["y"], info["width"], info["height"]) == (50, 20, 1280, 720)
