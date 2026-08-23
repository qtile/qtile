import pytest

from libqtile.config import Key
from libqtile.lazy import lazy
from test.helpers import BareConfig, Retry


class ShorcutInhibitorConfig(BareConfig):
    keys = [Key(["control"], key, lazy.group[key].toscreen()) for key in "abcd"]


KEY_A = 30
KEY_B = 48
MOD_CONTROL = 4


pytestmark = [
    pytest.mark.parametrize("test_client", ["shortcut-inhibitor"], indirect=True),
    pytest.mark.parametrize("wmanager", [ShorcutInhibitorConfig], indirect=True),
]


def test_shortcut_inhibitor(test_client, wmanager, virtual_keyboard):
    """Test that a wayland client can grab all keypresses"""

    def assert_group(name):
        assert wmanager.c.group.info()["name"] == name

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_windows(count):
        assert len(wmanager.c.windows()) == count

    assert_group("a")

    # Verify that keyboard events work
    virtual_keyboard.assert_ok("set_modifier control")
    virtual_keyboard.assert_ok(f"tap {KEY_B}")
    virtual_keyboard.assert_ok("clear_modifiers")
    assert_group("b")

    # Check that a client receives key presses
    test_client.assert_ok("show")
    wait_for_windows(1)
    virtual_keyboard.assert_ok(f"tap {KEY_A}")
    lines = test_client.send_read_until("get_keypress", "OK")
    assert lines
    assert lines[0] == f"key: {KEY_A} mods: 0"
    test_client.assert_ok("clear_keypress")

    # Check that a client does not receive bound keys
    virtual_keyboard.assert_ok("set_modifier control")
    virtual_keyboard.assert_ok(f"tap {KEY_A}")
    virtual_keyboard.assert_ok("clear_modifiers")
    lines = test_client.send_read_until("get_keypress", "OK")
    assert lines
    assert lines[0] == "key: 0 mods: 0"
    test_client.assert_ok("clear_keypress")

    # Confirm qtile handles the key binding
    assert_group("a")

    # Have client create a shortcut inhibitor
    test_client.assert_ok("inhibit")

    # Check that a client now receives bound keys
    wmanager.c.group["b"].toscreen()  # Window needs to be focused
    virtual_keyboard.assert_ok("set_modifier control")
    virtual_keyboard.assert_ok(f"tap {KEY_A}")
    virtual_keyboard.assert_ok("clear_modifiers")
    lines = test_client.send_read_until("get_keypress", "OK")
    assert lines
    assert lines[0] == f"key: {KEY_A} mods: {MOD_CONTROL}"
    test_client.assert_ok("clear_keypress")

    # Verify that qtile did not change groups
    assert_group("b")

    # Release the inhibitor and confirm that qtile swallows keys again
    test_client.assert_ok("uninhibit")
    virtual_keyboard.assert_ok("set_modifier control")
    virtual_keyboard.assert_ok(f"tap {KEY_A}")
    virtual_keyboard.assert_ok("clear_modifiers")
    lines = test_client.send_read_until("get_keypress", "OK")
    assert lines
    assert lines[0] == "key: 0 mods: 0"
    test_client.assert_ok("clear_keypress")

    # Qtile should swallow key press and switch group
    assert_group("a")
