"""
Regression test for keybinding keysym resolution in the Wayland C backend.

With multiple keyboard layouts configured (e.g. "us,ru") and a non-primary
layout active, a binding declared against the primary-layout keysym must still
fire when the corresponding physical key is pressed. The C backend resolves
keybinding keysyms against layout index 0 rather than the active layout
(qw/keyboard.c, qw_keyboard_handle_key); before that fix, pressing the physical
"r" key while the Russian layout was active yielded Cyrillic_ka and the binding
declared as ``Key([], "r", ...)`` stopped firing.

The test uses the virtual-keyboard protocol to attach a client-provided "us,ru"
keymap, switch the active layout to Russian, and inject a physical "r" press.
"""

import time

import pytest

from libqtile.config import Key
from libqtile.lazy import lazy
from test.helpers import BareConfig

# evdev keycodes (linux/input-event-codes.h).
KEY_R = 19
KEY_T = 20

# Keycode bindings use XKB keycodes (evdev + 8).
XKB_KEY_T = KEY_T + 8


class KeybindLayoutConfig(BareConfig):
    keys = [
        Key([], "r", lazy.group["b"].toscreen()),
        # Same scenario for a binding declared by raw keycode: it is converted
        # to a keysym at grab time (qw_server_get_sym_from_code, i.e. "t" under
        # the default layout), so runtime matching is keysym-based as well.
        Key([], XKB_KEY_T, lazy.group["c"].toscreen()),
    ]


keybind_layout_config = pytest.mark.parametrize("wmanager", [KeybindLayoutConfig], indirect=True)
pytestmark = pytest.mark.parametrize("test_client", ["virtual-keyboard"], indirect=True)


def wait_for_group(wmanager, name, timeout=5.0):
    """Poll the current group name until it matches or the timeout elapses."""
    deadline = time.monotonic() + timeout
    current = None
    while time.monotonic() < deadline:
        current = wmanager.c.group.info()["name"]
        if current == name:
            return current
        time.sleep(0.05)
    return current


@keybind_layout_config
def test_keybinding_fires_with_nonprimary_layout_active(wmanager, test_client):
    # Sanity check: we start on the first group.
    assert wmanager.c.group.info()["name"] == "a"

    # Attach a us,ru keymap to the virtual keyboard and make Russian (layout
    # index 1) the active layout.
    test_client.assert_ok("keymap us,ru")
    test_client.assert_ok("group 1")

    # Press the physical "r" key. Resolved against layout 0 this is keysym "r",
    # which matches the configured binding; against the active Russian layout it
    # would be Cyrillic_ka and would not match.
    test_client.assert_ok(f"press {KEY_R}")
    test_client.assert_ok(f"release {KEY_R}")

    assert wait_for_group(wmanager, "b") == "b"


@keybind_layout_config
def test_keycode_binding_fires_with_nonprimary_layout_active(wmanager, test_client):
    """
    Bindings declared by raw keycode go through the same keysym matching: the
    keycode is resolved to a keysym once at grab time, and key presses must
    resolve to that same keysym regardless of the active layout. Before the
    layout-0 fix, pressing the physical "t" key with Russian active yielded
    Cyrillic_ie and the ``Key([], 28, ...)`` binding stopped firing too.
    """
    assert wmanager.c.group.info()["name"] == "a"

    test_client.assert_ok("keymap us,ru")
    test_client.assert_ok("group 1")

    test_client.assert_ok(f"press {KEY_T}")
    test_client.assert_ok(f"release {KEY_T}")

    assert wait_for_group(wmanager, "c") == "c"
