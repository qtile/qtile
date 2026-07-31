import pytest

from libqtile import hook, widget
from libqtile.bar import Bar
from libqtile.config import Screen
from libqtile.confreader import Config
from test.helpers import Retry


class SystemBellConfig(Config):
    bell_widget = widget.TextBox("", name="bell")

    def update_widget(window):  # noqa: N805
        if window is None:
            SystemBellConfig.bell_widget.update("No window")
        else:
            SystemBellConfig.bell_widget.update(f"{window.wid}")

    screens = [Screen(top=Bar([bell_widget], 20))]

    hook.subscribe.system_bell(update_widget)


pytestmark = [
    pytest.mark.parametrize("test_client", ["system-bell"], indirect=True),
    pytest.mark.parametrize("wmanager", [SystemBellConfig], indirect=True),
]


def test_system_bell_no_surface(wmanager, test_client):
    """If system bell is rung with no surface attached, the hook will receive None."""
    test_client.assert_ok("ring")
    assert wmanager.c.widget["bell"].info()["text"] == "No window"


def test_system_bell_with_window(wmanager, test_client):
    """If system bell is rung with no surface attached, the hook will receive the relevant window."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) == 1

    # Create a client window and get its ID
    test_client.assert_ok("show")
    wait_for_window()
    wid = wmanager.c.windows()[0]["id"]

    # Ring the bell and check that the widget receives the correct window
    test_client.assert_ok("ring")
    assert wmanager.c.widget["bell"].info()["text"] == f"{wid}"
