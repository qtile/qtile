import libqtile
from libqtile.widget import WindowCount


def test_window_count(manager_nospawn):
    class WindowCountConf(libqtile.confreader.Config):
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar([WindowCount()], 10)
            )
        ]

    manager_nospawn.start(WindowCountConf)

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
