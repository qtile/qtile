import pytest

import libqtile.config
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_focus_path, assert_focused


class MatrixConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [layout.Matrix(columns=2)]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


matrix_config = pytest.mark.parametrize("manager", [MatrixConfig], indirect=True)


@matrix_config
def test_matrix_simple(manager):
    manager.test_window("one")
    assert manager.c.layout.info()["rows"] == [["one"]]
    manager.test_window("two")
    assert manager.c.layout.info()["rows"] == [["one", "two"]]
    manager.test_window("three")
    assert manager.c.layout.info()["rows"] == [["one", "two"], ["three"]]


@matrix_config
def test_matrix_navigation(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")
    manager.test_window("five")
    manager.c.layout.right()
    assert manager.c.layout.info()["current_window"] == (0, 2)
    manager.c.layout.up()
    assert manager.c.layout.info()["current_window"] == (0, 1)
    manager.c.layout.up()
    assert manager.c.layout.info()["current_window"] == (0, 0)
    manager.c.layout.up()
    assert manager.c.layout.info()["current_window"] == (0, 2)
    manager.c.layout.down()
    assert manager.c.layout.info()["current_window"] == (0, 0)
    manager.c.layout.down()
    assert manager.c.layout.info()["current_window"] == (0, 1)
    manager.c.layout.right()
    assert manager.c.layout.info()["current_window"] == (1, 1)
    manager.c.layout.right()
    assert manager.c.layout.info()["current_window"] == (0, 1)
    manager.c.layout.left()
    assert manager.c.layout.info()["current_window"] == (1, 1)


@matrix_config
def test_matrix_add_remove_columns(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.test_window("three")
    manager.test_window("four")
    manager.test_window("five")
    manager.c.layout.add()
    assert manager.c.layout.info()["rows"] == [["one", "two", "three"], ["four", "five"]]
    manager.c.layout.delete()
    assert manager.c.layout.info()["rows"] == [["one", "two"], ["three", "four"], ["five"]]


@matrix_config
def test_matrix_window_focus_cycle(manager):
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


@matrix_config
def test_matrix_next_no_clients(manager):
    manager.c.layout.next()


@matrix_config
def test_matrix_previous_no_clients(manager):
    manager.c.layout.previous()


def test_unknown_client():
    """Simple test to get coverage to 100%!"""
    matrix = layout.Matrix()

    # The layout will not configure an unknown client.
    # Without the return statement in "configure" the following
    # code would result in an error
    assert matrix.configure("fakeclient", None) is None
