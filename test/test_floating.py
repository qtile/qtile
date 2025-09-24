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
