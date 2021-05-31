import libqtile
from libqtile.widget import WindowCount


def test_window_count(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    config.screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar([WindowCount()], 10)
            )
        ]

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
