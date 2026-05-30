import pytest

from libqtile import hook, widget
from libqtile.bar import Bar
from libqtile.config import Screen
from libqtile.confreader import Config


class IdleConfig(Config):
    idle_widget = widget.TextBox("False", name="idle")

    def update_widget(inhibited):  # noqa: N805
        IdleConfig.idle_widget.update(f"{inhibited}")

    screens = [Screen(top=Bar([idle_widget], 20))]

    hook.subscribe.idle_inhibitor_change(update_widget)


idle_config = pytest.mark.parametrize("wmanager", [IdleConfig], indirect=True)
pytestmark = pytest.mark.parametrize("test_client", ["idle-client"], indirect=True)


def test_idle_notify(wmanager, test_client):
    """Test idle messages sent by compositor to clients."""
    # Request idle notification timer
    test_client.assert_ok("watch 100")

    # Confirm client receives idle message
    test_client.assert_line("idled")

    # Trigger activity and verify resumed message
    wmanager.c.core.idle_notify_activity()
    wmanager.c.core.flush()
    test_client.assert_line("resumed")

    # Unsubscribe notification timer
    test_client.assert_ok("unwatch")

    # Idle notify timeout was 100ms so we wait for 200ms and confirm
    # there's no IDLED event
    test_client.assert_no_text()


def test_idle_inhibit_client(wmanager, test_client):
    """Test idle messages not sent by compositor to clients when inhibited."""
    # Request an inhibitor before idle notification timer
    test_client.assert_ok("inhibit")
    test_client.assert_ok("watch 100")

    # Inhibited so no messages
    test_client.assert_no_text()

    # Remove inhibitor and verify we now get idle messages
    test_client.assert_ok("uninhibit")
    test_client.assert_line("idled")


def test_idle_inhibit_qtile(wmanager, test_client):
    """
    Test idle messages not sent by compositor to clients when using internal inhibitor.
    """
    # Request an inhibitor before idle notification timer
    wmanager.c.core.set_idle_inhibitor()
    test_client.assert_ok("watch 100")

    # Inhibited so no messages
    test_client.assert_no_text()

    # Remove inhibitor and verify we now get idle messages
    wmanager.c.core.remove_idle_inhibitor()
    test_client.assert_line("idled")


@idle_config
def test_idle_inhibit_hooks(wmanager, test_client):
    assert wmanager.c.widget["idle"].info()["text"] == "False"
    test_client.assert_ok("inhibit")
    assert wmanager.c.widget["idle"].info()["text"] == "True"
    test_client.assert_ok("uninhibit")
    assert wmanager.c.widget["idle"].info()["text"] == "False"
