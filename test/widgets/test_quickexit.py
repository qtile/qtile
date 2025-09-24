import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget
from libqtile.ipc import IPCError


def test_trigger_and_cancel(manager_nospawn, minimal_conf_noscreen):
    # Set a long interval to allow for unanticipated delays in testing environment
    qewidget = widget.QuickExit(timer_interval=100)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([qewidget], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    # Default text
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ shutdown ]"

    # Click widget to start countdown
    topbar.fake_button_press(0, 0, button=1)
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ 4 seconds ]"

    # Click widget again to cancel countdown
    topbar.fake_button_press(0, 0, button=1)
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ shutdown ]"


def test_exit(manager_nospawn, minimal_conf_noscreen):
    # Set a short interval and start so widget exits immediately
    qewidget = widget.QuickExit(timer_interval=0.001, countdown_start=1)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([qewidget], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    # Click widget to start countdown
    topbar.fake_button_press(0, 0, button=1)

    manager_nospawn.proc.join()

    # Trying to access bar should now give IPCError or a ConnectionResetError
    # as qtile has shutdown
    with pytest.raises((IPCError, ConnectionResetError)):
        assert topbar.info()
