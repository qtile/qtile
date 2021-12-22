import pytest

import libqtile
from libqtile.confreader import Config
from libqtile.widget import WindowCount


class DifferentScreens(Config):
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [
        libqtile.layout.Stack(num_stacks=1),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    fake_screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    WindowCount(),
                ],
                20,
            ),
            x=0,
            y=0,
            width=300,
            height=300,
        ),
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    WindowCount(),
                ],
                20,
            ),
            x=0,
            y=300,
            width=300,
            height=300,
        ),
    ]
    auto_fullscreen = True


different_screens = pytest.mark.parametrize("manager", [DifferentScreens], indirect=True)


@different_screens
def test_different_screens(manager):
    # Put one window on screen 0
    manager.c.to_screen(0)
    manager.test_window("one")

    # Put two windows on screen 1
    manager.c.to_screen(1)
    manager.test_window("two")
    manager.test_window("three")

    assert manager.c.screen[0].widget["windowcount"].get() == "1"
    assert manager.c.screen[1].widget["windowcount"].get() == "2"


def test_window_count(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([WindowCount()], 10))]

    manager_nospawn.start(config)

    # No windows opened
    assert int(manager_nospawn.c.widget["windowcount"].get()) == 0

    # Add a window and check count
    one = manager_nospawn.test_window("one")
    assert int(manager_nospawn.c.widget["windowcount"].get()) == 1

    # Add a window and check text
    two = manager_nospawn.test_window("two")
    assert manager_nospawn.c.widget["windowcount"].get() == "2"

    # Change to empty group
    manager_nospawn.c.group["b"].toscreen()
    assert int(manager_nospawn.c.widget["windowcount"].get()) == 0

    # Change back to group
    manager_nospawn.c.group["a"].toscreen()
    assert int(manager_nospawn.c.widget["windowcount"].get()) == 2

    # Close all windows and check count is 0 and widget not displayed
    manager_nospawn.kill_window(one)
    manager_nospawn.kill_window(two)
    assert int(manager_nospawn.c.widget["windowcount"].get()) == 0


def test_attribute_errors():
    def no_op(*args, **kwargs):
        pass

    wc = WindowCount()
    wc.update = no_op

    wc._count = 1
    wc._wincount()
    assert wc._count == 0

    wc._count = 1
    wc._win_killed(None)
    assert wc._count == 0
