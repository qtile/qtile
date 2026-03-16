from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libqtile.backend.macos.inputs import InputManager


@pytest.fixture
def input_manager():
    qtile = MagicMock()
    core = MagicMock()
    return InputManager(qtile, core)


def test_keysym_space(input_manager):
    assert input_manager.keysym_from_name("space") == 49


def test_keysym_return(input_manager):
    assert input_manager.keysym_from_name("return") == 36


def test_keysym_kp_enter(input_manager):
    assert input_manager.keysym_from_name("kp_enter") == 76


def test_keysym_escape(input_manager):
    assert input_manager.keysym_from_name("escape") == 53


def test_keysym_kp_0(input_manager):
    assert input_manager.keysym_from_name("kp_0") == 82


def test_keysym_unknown_returns_zero(input_manager):
    assert input_manager.keysym_from_name("nonexistent_key_xyz") == 0


def test_keysym_case_insensitive(input_manager):
    # The mapping uses .lower(), so "Space" should equal "space"
    assert input_manager.keysym_from_name("Space") == 49
    assert input_manager.keysym_from_name("RETURN") == 36


# ---------------------------------------------------------------------------
# grab_key / ungrab_key / ungrab_keys / process_key_event
# ---------------------------------------------------------------------------


def _make_key(key_name: str, modifiers=None):
    """Build a minimal key-like object for grab/ungrab tests."""
    key = MagicMock()
    key.key = key_name
    key.modifiers = modifiers or []
    return key


def test_grab_key_adds_to_set(input_manager):
    """grab_key adds the (keycode, mask) tuple to grabbed_keys."""
    input_manager.core._translate_mask.return_value = 0
    key = _make_key("space")
    input_manager.grab_key(key)
    assert (49, 0) in input_manager.grabbed_keys


def test_ungrab_key_removes_from_set(input_manager):
    """ungrab_key removes the (keycode, mask) tuple from grabbed_keys."""
    input_manager.core._translate_mask.return_value = 0
    key = _make_key("space")
    input_manager.grab_key(key)
    input_manager.ungrab_key(key)
    assert (49, 0) not in input_manager.grabbed_keys


def test_ungrab_key_idempotent(input_manager):
    """ungrab_key on a never-grabbed key does not raise."""
    input_manager.core._translate_mask.return_value = 0
    key = _make_key("escape")
    input_manager.ungrab_key(key)  # should not raise


def test_ungrab_keys_clears_all(input_manager):
    """ungrab_keys() leaves grabbed_keys empty."""
    input_manager.core._translate_mask.return_value = 0
    for name in ("space", "return", "escape"):
        input_manager.grab_key(_make_key(name))
    assert len(input_manager.grabbed_keys) == 3
    input_manager.ungrab_keys()
    assert len(input_manager.grabbed_keys) == 0


def test_process_key_event_dispatches_grabbed(input_manager):
    """process_key_event returns True and calls call_soon_threadsafe for a grabbed key."""
    input_manager.core._translate_mask.return_value = 0
    key = _make_key("space")
    input_manager.grab_key(key)
    result = input_manager.process_key_event(0, 49)
    assert result is True
    input_manager.qtile.call_soon_threadsafe.assert_called_once_with(
        input_manager.qtile.process_key_event, 49, 0
    )


def test_process_key_event_ignores_ungrabbed(input_manager):
    """process_key_event returns False and does not call call_soon_threadsafe for ungrabbed."""
    result = input_manager.process_key_event(0, 49)
    assert result is False
    input_manager.qtile.call_soon_threadsafe.assert_not_called()
